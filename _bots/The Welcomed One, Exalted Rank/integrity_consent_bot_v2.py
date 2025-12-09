#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrity Consent Bot v2 - Penelope Data Extraction with English/Spanish Support
Extracts client data from Penelope, creates consent forms, and uploads to TherapyNotes
"""

import os, sys, re, time, tempfile, threading, queue, json
import datetime
from datetime import datetime as DT
from dataclasses import dataclass
from typing import Optional, Dict, List
from pathlib import Path
import pandas as pd

# GUI imports
try:
    import tkinter as tk
    from tkinter import filedialog, scrolledtext, messagebox
    from tkinter import ttk
except Exception as e:
    print("Tkinter failed to load. You may need to install/repair Python with Tk support.")
    print("Error:", e)
    sys.exit(1)

APP_TITLE = "Consent Form Bot"
MAROON = "#800000"
PN_DEFAULT_URL = "https://integrityseniorservices.athena-us.com/acm_loginControl"

# Selenium lazy imports
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

def _ts(): return time.strftime("[%H:%M:%S] ")

def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", (name or "").strip())

def ensure_output_dir():
    """Creates output directory for consent forms"""
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    output_dir = os.path.join(desktop_dir, "Consent form bot output")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

# ===================== PENELOPE CLIENT CLASS =====================
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
        """Find and click the navSearch button in any available frame."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        d, w = self.driver, self.wait
        
        try:
            d.switch_to.default_content()
            self.log(_ts() + "[GO_SEARCH] Looking for navSearch button...")
            
            # Wait for page to fully load
            time.sleep(3)
            
            # Try to find the button by searching all frames
            frames = d.find_elements(By.TAG_NAME, "frame") + d.find_elements(By.TAG_NAME, "iframe")
            self.log(_ts() + f"[GO_SEARCH] Found {len(frames)} total frame(s)")
            
            # Try each frame to find navSearch button
            for fr in frames:
                try:
                    d.switch_to.default_content()
                    d.switch_to.frame(fr)
                    
                    try:
                        search_btn = d.find_element(By.ID, "navSearch")
                        if search_btn and search_btn.is_displayed():
                            self.log(_ts() + "[GO_SEARCH] Found navSearch button in frame")
                            
                            # Click it
                            try:
                                search_btn.click()
                            except:
                                d.execute_script("arguments[0].click();", search_btn)
                            
                            self.log(_ts() + "[GO_SEARCH] Clicked navSearch button")
                            d.switch_to.default_content()
                            
                            # Wait for search page to load
                            WebDriverWait(d, 15).until(
                                EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id"))
                            )
                            d.switch_to.default_content()
                            
                            self.log(_ts() + "[GO_SEARCH] Search page loaded successfully")
                            return True
                    except:
                        continue
                        
                except:
                    continue
            
            # If we get here, couldn't find the button
            self.log(_ts() + "[GO_SEARCH][ERR] Could not find navSearch button in any frame")
            d.switch_to.default_content()
            return False
            
        except Exception as e:
            self.log(_ts() + f"[GO_SEARCH][ERR] {e}")
            try:
                d.switch_to.default_content()
            except:
                pass
            return False

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

    def enter_individual_id_and_go(self, indiv_id: str, timeout: int = 12) -> bool:
        """
        Individual > Individual ID: enter ID # > Press Go > WAIT for dropdown/results.
        EXACT COPY FROM COUNSELOR ASSIGNMENT BOT
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
                    if _into_frame() and _activate_individual_tab():
                        pass
                    else:
                        raise TimeoutException("Could not activate Individual tab")

                # The ID field should already be focused and cleared from _activate_individual_tab
                # Just get a fresh reference and enter the ID
                id_input = WebDriverWait(d, 6).until(EC.element_to_be_clickable((By.NAME, "txtKIndID")))
                
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
                
                # Enhanced stale element handling for ID input with VERIFICATION
                id_entered_successfully = False
                for retry in range(3):
                    try:
                        # Re-find the element each time to avoid stale references
                        id_input = WebDriverWait(d, 6).until(EC.element_to_be_clickable((By.NAME, "txtKIndID")))
                        
                        # Clear the field first to ensure clean state
                        try:
                            id_input.clear()
                        except Exception:
                            d.execute_script("arguments[0].value = '';", id_input)
                        
                        # Type the ID
                        id_input.send_keys(_id)
                        
                        # VERIFY the ID was actually entered
                        import time
                        time.sleep(0.2)  # Brief pause for the value to register
                        entered_value = id_input.get_attribute("value") or ""
                        
                        if entered_value.strip() == _id:
                            log(f"[INDIV] ✓ VERIFIED: ID '{_id}' successfully entered (field shows: '{entered_value}')")
                            id_entered_successfully = True
                            break
                        else:
                            log(f"[INDIV][WARN] ID mismatch! Expected '{_id}', but field shows '{entered_value}'. Retry {retry + 1}/3")
                            if retry < 2:
                                time.sleep(0.3)
                                if not _into_frame():
                                    raise
                                continue
                            else:
                                log(f"[INDIV][ERROR] Failed to enter correct ID after 3 attempts!")
                                raise ValueError(f"ID entry verification failed: expected '{_id}', got '{entered_value}'")
                        
                    except StaleElementReferenceException:
                        if retry < 2:
                            log(f"[INDIV][WARN] Stale element on retry {retry + 1}, re-finding...")
                            if not _into_frame():
                                raise
                            continue
                        else:
                            raise
                    except Exception as e:
                        if retry < 2:
                            log(f"[INDIV][WARN] Input error on retry {retry + 1}: {e}, re-finding...")
                            if not _into_frame():
                                raise
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
                        
                        # Check if multiple results (could indicate wrong client selection)
                        result_links = d.find_elements(By.XPATH, "//div[@id='results']//a[normalize-space(text())!='']")
                        if len(result_links) > 1:
                            log(f"[INDIV][WARN] Found {len(result_links)} result(s) - will select first ISWS (non-IPS) match")
                        elif len(result_links) == 1:
                            log(f"[INDIV] Found exactly 1 result - good!")
                        else:
                            log(f"[INDIV][WARN] Could not count result links")
                    else:
                        log(f"[INDIV][WARN] Results element found but appears empty")
                except Exception as e:
                    log(f"[INDIV][WARN] Could not read results details: {e}")

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
        EXACT COPY FROM COUNSELOR ASSIGNMENT BOT
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

    def extract_client_data(self) -> Dict[str, str]:
        """Extract language, date, and name from the current client profile page"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            d = self.driver
            log = self.log
            
            # Ensure we're in the content frame
            d.switch_to.default_content()
            WebDriverWait(d, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
            
            # Extract language from profile
            language = self._extract_language(d)
            log(_ts() + f"[PN] Language detected: {language}")
            
            # Extract date from notes
            date = self._extract_accepted_date(d)
            log(_ts() + f"[PN] Date extracted from notes: {date}")
            
            # Extract client name
            client_name = self._extract_client_name(d)
            log(_ts() + f"[PN] Client name: {client_name}")
            
            d.switch_to.default_content()
            return {
                "language": language,
                "date": date,
                "client_name": client_name
            }
        except Exception as e:
            self.log(_ts() + f"[PN][ERR] Failed to extract data: {e}")
            try:
                d.switch_to.default_content()
            except:
                pass
            return {}

    def _extract_language(self, driver) -> str:
        """Extract client's preferred language from profile"""
        try:
            from selenium.webdriver.common.by import By
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            if "spanish" in page_text or "español" in page_text or "espanol" in page_text:
                # Double-check by searching for language field
                try:
                    lang_elems = driver.find_elements(By.XPATH, "//*[contains(., 'Spanish') or contains(., 'Español')]")
                    if lang_elems:
                        return "Spanish"
                except:
                    pass
                return "Spanish"
            else:
                return "English"
        except Exception:
            return "English"

    def _extract_accepted_date(self, driver) -> str:
        """Extract MOST RECENT date from notes containing 'Accepted' variations"""
        try:
            from selenium.webdriver.common.by import By
            
            # Search for elements containing "Accepted SERVICES" variants - must be specifically about accepting services
            # Include common misspellings and abbreviations
            accepted_keywords = [
                "accepted services",  # Most common
                "accepted srvs",
                "accepted srv",
                "acptd services",  # Abbreviation
                "acptd srvs",  # Abbreviation
                "acptd srv",  # Abbreviation
                "client accepted services",
                "ct accepted services",  # CT ACCEPTED services
                "ct accepted srvs",
                "client acptd",  # Alternative abbreviation
                "accptd services",  # Typo
                "accepted serv",  # Shortened
            ]
            
            # Get all text on the page
            found_dates = []  # List of (date_string, full_line_text, line_index) tuples
            
            def extract_date_from_line(line, line_index):
                """Extract date from a line, checking start first, then anywhere"""
                # Pattern to match date at start of line (most common format)
                date_pattern_start = r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
                # Pattern to match date anywhere in line
                date_pattern_anywhere = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
                
                # First try to match date at the start of the line (most common format for notes)
                match_start = re.match(date_pattern_start, line.strip())
                if match_start:
                    return match_start.group(1)
                else:
                    # If no date at start, look for dates anywhere in the line
                    dates_in_line = re.findall(date_pattern_anywhere, line)
                    if dates_in_line:
                        # Return first date found on this line
                        return dates_in_line[0]
                return None
            
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text
                lines = page_text.split('\n')
                
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    # Check if this line contains any "Accepted" keyword (case-insensitive)
                    # Also check for fuzzy matches to handle typos
                    has_accepted_keyword = False
                    for keyword in accepted_keywords:
                        if keyword in line_lower:
                            has_accepted_keyword = True
                            break
                    
                    # ALSO check for pattern: "accepted" + "service" (allows for typos in between)
                    if not has_accepted_keyword:
                        # Look for "accepted" or "acptd" followed by "service" or "srv" (with possible typos)
                        if re.search(r'ac(pt|ce)te?d?\s+(serv|srv)', line_lower):
                            # Additional validation: should NOT be "accepted the case" or "accepted appointment"
                            if not re.search(r'accepted the (case|appointment)', line_lower):
                                has_accepted_keyword = True
                    
                    # When we find an "Accepted" keyword, check current line AND adjacent lines for dates
                    if has_accepted_keyword:
                        # Check current line first
                        date_str = extract_date_from_line(line, i)
                        if date_str:
                            found_dates.append((date_str, line, i))
                            self.log(_ts() + f"[DATE-DEBUG] Found ACCEPTED date on current line: {date_str} on line {i}: {line[:100]}")
                        else:
                            # If no date on current line, check previous line (common in notes where date is on separate line)
                            if i > 0:
                                prev_date = extract_date_from_line(lines[i-1], i-1)
                                if prev_date:
                                    found_dates.append((prev_date, lines[i-1], i-1))
                                    self.log(_ts() + f"[DATE-DEBUG] Found ACCEPTED date on previous line: {prev_date} on line {i-1}: {lines[i-1][:100]}")
                            # Also check next line as fallback
                            if i < len(lines) - 1:
                                next_date = extract_date_from_line(lines[i+1], i+1)
                                if next_date:
                                    found_dates.append((next_date, lines[i+1], i+1))
                                    self.log(_ts() + f"[DATE-DEBUG] Found ACCEPTED date on next line: {next_date} on line {i+1}: {lines[i+1][:100]}")
            except Exception as e:
                self.log(_ts() + f"[DATE-DEBUG] Error extracting dates: {str(e)}")
                pass
            
            # If we found any dates, parse them and return the most recent
            if found_dates:
                try:
                    def parse_date(date_str):
                        """Parse date string to datetime object for comparison"""
                        try:
                            # Try MM/DD/YYYY format
                            for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"]:
                                try:
                                    return DT.strptime(date_str, fmt)
                                except:
                                    continue
                            return None
                        except:
                            return None
                    
                    # Parse all dates and find the most recent
                    parsed_dates = []
                    for date_str, line_text, line_idx in found_dates:
                        parsed = parse_date(date_str)
                        if parsed:
                            parsed_dates.append((parsed, date_str, line_idx))
                            self.log(_ts() + f"[DATE-DEBUG] Successfully parsed date: {date_str} -> {parsed.strftime('%m/%d/%Y')} (line {line_idx})")
                        else:
                            self.log(_ts() + f"[DATE-DEBUG] Failed to parse date: {date_str} (line {line_idx})")
                    
                    if parsed_dates:
                        # Sort by parsed datetime and return the most recent
                        parsed_dates.sort(key=lambda x: x[0], reverse=True)
                        most_recent_parsed, most_recent_date, most_recent_line = parsed_dates[0]
                        
                        self.log(_ts() + f"[DATE-DEBUG] Found {len(parsed_dates)} valid dates. Most recent: {most_recent_date} (line {most_recent_line}) from {most_recent_parsed.strftime('%m/%d/%Y')}")
                        
                        # Expand 2-digit years to 4-digit years
                        if len(most_recent_date.split('/')[-1]) == 2:
                            # Convert "9/22/25" to "9/22/2025"
                            parts = most_recent_date.split('/')
                            if len(parts) == 3:
                                month, day, year = parts
                                # Assume years 00-30 are 2000-2030, years 31-99 are 1931-1999
                                year_int = int(year)
                                if year_int <= 30:
                                    year_str = f"20{year}"
                                else:
                                    year_str = f"19{year}"
                                return f"{month}/{day}/{year_str}"
                        
                        return most_recent_date
                except Exception as e:
                    self.log(_ts() + f"[DATE-DEBUG] Error parsing dates: {str(e)}")
                    pass
                
                # If parsing fails, try to parse dates manually and compare as strings
                # This is a fallback - we'll try to find the most recent by comparing date strings
                self.log(_ts() + f"[DATE-DEBUG] Date parsing failed, attempting fallback comparison with {len(found_dates)} dates")
                # Sort by line index (assuming notes are in reverse chronological order - newest first)
                # But also try to parse and compare if possible
                try:
                    # Try one more time with a simpler approach - just compare the dates as strings
                    # by converting to a sortable format
                    def date_to_sortable(date_str):
                        """Convert date string to sortable format for comparison"""
                        parts = date_str.replace('-', '/').split('/')
                        if len(parts) == 3:
                            month, day, year = parts
                            year = year if len(year) == 4 else ('20' + year if int(year) <= 30 else '19' + year)
                            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        return ""
                    
                    sortable_dates = []
                    for date_str, line_text, line_idx in found_dates:
                        sortable = date_to_sortable(date_str)
                        if sortable:
                            sortable_dates.append((sortable, date_str))
                    
                    if sortable_dates:
                        sortable_dates.sort(reverse=True)  # Most recent first
                        most_recent_date = sortable_dates[0][1]
                        self.log(_ts() + f"[DATE-DEBUG] Fallback: Selected most recent date: {most_recent_date}")
                        
                        # Expand 2-digit years
                        if len(most_recent_date.split('/')[-1]) == 2:
                            parts = most_recent_date.split('/')
                            if len(parts) == 3:
                                month, day, year = parts
                                year_int = int(year)
                                if year_int <= 30:
                                    year_str = f"20{year}"
                                else:
                                    year_str = f"19{year}"
                                return f"{month}/{day}/{year_str}"
                        return most_recent_date
                except:
                    pass
                
                # Last resort: return the last one found (assuming notes are in reverse chronological order)
                last_date = found_dates[-1][0]
                self.log(_ts() + f"[DATE-DEBUG] Last resort: Using last found date: {last_date}")
                # Expand 2-digit years to 4-digit years
                if len(last_date.split('/')[-1]) == 2:
                    parts = last_date.split('/')
                    if len(parts) == 3:
                        month, day, year = parts
                        year_int = int(year)
                        if year_int <= 30:
                            year_str = f"20{year}"
                        else:
                            year_str = f"19{year}"
                        return f"{month}/{day}/{year_str}"
                return last_date
            
            # Return today's date as fallback
            self.log(_ts() + f"[DATE-DEBUG] No dates found, returning today's date")
            return DT.now().strftime("%m/%d/%Y")
        except Exception as e:
            self.log(_ts() + f"[DATE-DEBUG] Exception in _extract_accepted_date: {str(e)}")
            return DT.now().strftime("%m/%d/%Y")

    def _extract_client_name(self, driver) -> str:
        """Extract client's name from profile"""
        try:
            from selenium.webdriver.common.by import By
            # Try various selectors for client name - h3 is the actual client name on profile page
            selectors = [
                "//h3",  # Client name is in h3 (e.g., "Ben Doe")
                "//h1",
                "//h2",
                "//*[@id='name']",
                "//*[@class='name']"
            ]
            for sel in selectors:
                try:
                    elem = driver.find_element(By.XPATH, sel)
                    name = elem.text.strip()
                    # Skip generic titles
                    if name and len(name) > 2 and "profile" not in name.lower():
                        return name
                except:
                    continue
            return "Unknown Client"
        except:
            return "Unknown Client"


# ===================== PDF FILLING =====================

def fill_and_flatten_pdf(template_path, output_path, client_name, date, log):
    """Fill PDF using exact method from original consent bot"""
    try:
        from pdfrw import PdfReader, PdfWriter, PdfString, PdfDict, PdfName, PdfObject
        
        def fill_pdf_locked(template_path, output_path, field_values, log):
            """Fill PDF fields and make read-only - EXACT FROM ORIGINAL BOT"""
            try:
                def norm(s): return " ".join(str(s or "").strip().lower().split())
                wanted = {norm(k): (k, v) for k, v in field_values.items()}

                pdf = PdfReader(template_path)
                # Ask viewers to regenerate appearances
                try:
                    if pdf.Root and pdf.Root.AcroForm:
                        pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfObject("true")))
                    else:
                        pdf.Root.AcroForm = PdfDict(NeedAppearances=PdfObject("true"))
                except Exception:
                    pass

                # Collect fields
                norm_to_annots = {}
                all_field_names = []  # Debug: collect all field names
                for page in pdf.pages:
                    annots = getattr(page, "Annots", None)
                    if not annots:
                        continue
                    for annot in annots:
                        if getattr(annot, "Subtype", None) != PdfName.Widget or not getattr(annot, "T", None):
                            continue
                        raw_name = annot.T.to_unicode() if hasattr(annot, "to_unicode") else str(annot.T)
                        key_raw = str(raw_name).strip("()")
                        all_field_names.append(key_raw)  # Debug
                        key_norm = norm(key_raw)
                        norm_to_annots.setdefault(key_norm, []).append(annot)
                
                # Log all found fields for debugging
                if all_field_names:
                    log(_ts() + f"  [DEBUG] Found PDF fields: {', '.join(all_field_names[:10])}" + ("..." if len(all_field_names) > 10 else ""))

                # Set values (fuzzy)
                filled_any = False
                for want_norm, (orig_key, value) in wanted.items():
                    if value is None:
                        continue
                    value_str = str(value)
                    targets = []
                    
                    # Try exact match first
                    if want_norm in norm_to_annots:
                        targets.extend(norm_to_annots[want_norm])
                    
                    # Try partial matching - check if any key contains our search term
                    if not targets:
                        for k_norm, ann_list in norm_to_annots.items():
                            if want_norm in k_norm or k_norm in want_norm:
                                targets.extend(ann_list)
                    
                    # More aggressive partial matching for Spanish fields
                    # Split the wanted key into words and try to match any field containing those words
                    if not targets:
                        want_words = want_norm.split()
                        for k_norm, ann_list in norm_to_annots.items():
                            k_words = k_norm.split()
                            # Check if any word from our wanted key appears in the field name
                            if any(word in k_words or word in k_norm for word in want_words if len(word) > 2):
                                targets.extend(ann_list)
                    
                    # Last resort: if looking for name or date, try very common variations
                    if not targets:
                        if "name" in want_norm or "nombre" in want_norm or "cliente" in want_norm:
                            # Try to find any field with name, nombre, cliente, print, nombre, etc.
                            for k_norm, ann_list in norm_to_annots.items():
                                if any(word in k_norm for word in ["name", "nombre", "cliente", "print", "imprimir"]):
                                    targets.extend(ann_list)
                        elif "date" in want_norm or "fecha" in want_norm:
                            # Try to find any field with date or fecha
                            for k_norm, ann_list in norm_to_annots.items():
                                if any(word in k_norm for word in ["date", "fecha"]):
                                    targets.extend(ann_list)
                    
                    if not targets:
                        log(_ts() + f'  [WARN] No PDF field matched "{orig_key}".')
                        continue
                    
                    # ONLY fill the FIRST matching target (top field only)
                    # Sort targets by position (top to bottom) - fields with higher Y coordinates are at top
                    try:
                        sorted_targets = []
                        for annot in targets:
                            try:
                                rect = annot.Rect
                                if rect and len(rect) >= 4:
                                    y_coord = float(rect[3])  # Top Y coordinate
                                    sorted_targets.append((y_coord, annot))
                            except:
                                # If we can't get coordinates, just use the first one
                                sorted_targets.append((999999, annot))
                        sorted_targets.sort(reverse=True)  # Highest Y first (top of page)
                        targets = [annot for _, annot in sorted_targets]
                    except:
                        # If sorting fails, just use first target
                        pass
                    
                    # Fill only the first (topmost) target
                    first_target = targets[0] if targets else None
                    if first_target:
                        try:
                            pdf_value = PdfString.encode(value_str)
                            first_target.update(PdfDict(V=pdf_value, DV=pdf_value))
                            filled_any = True
                            log(_ts() + f'  [SUCCESS] Matched "{orig_key}" to first PDF field (top field only)')
                        except Exception as e:
                            log(_ts() + f'  [WARN] Failed to set "{orig_key}": {e}')

                # Make all fields read-only
                READONLY_BIT = 1
                for page in pdf.pages:
                    annots = getattr(page, "Annots", None)
                    if not annots:
                        continue
                    for annot in annots:
                        try:
                            if getattr(annot, "Subtype", None) == PdfName.Widget:
                                ff = 0
                                try:
                                    ff_raw = annot.get("/Ff", 0)
                                    if ff_raw is not None:
                                        ff = int(str(ff_raw))
                                except Exception:
                                    ff = 0
                                annot.update(PdfDict(Ff=ff | READONLY_BIT))
                        except Exception as e:
                            log(_ts() + f"  [WARN] Could not set ReadOnly on a field: {e}")

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                PdfWriter().write(output_path, pdf)
                
                if not filled_any:
                    log(_ts() + "  [INFO] No fields were filled (names may not have matched).")
                else:
                    log(_ts() + "  [INFO] Fields set to read-only (not fillable).")
                return True
            except Exception as e:
                log(_ts() + f"  [ERROR] fill_pdf failed: {e}")
                return False
        
        def flatten_pdf_preserving_values(input_pdf, output_pdf, log):
            """Flatten PDF - EXACT FROM ORIGINAL BOT"""
            try:
                from reportlab.pdfgen import canvas as rl_canvas
                from pdfrw import PageMerge

                pdf = PdfReader(input_pdf)
                pages = pdf.pages or []

                # Build overlay with drawn text where fields are
                tmp_overlay = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                tmp_overlay_path = tmp_overlay.name
                tmp_overlay.close()
                c = rl_canvas.Canvas(tmp_overlay_path)

                for page in pages:
                    mb = page.MediaBox
                    llx, lly, urx, ury = [float(x) for x in (mb[0], mb[1], mb[2], mb[3])]
                    width, height = (urx - llx), (ury - lly)
                    try:
                        c.setPageSize((width, height))
                    except Exception:
                        pass

                    annots = getattr(page, "Annots", None)
                    if annots:
                        for annot in annots:
                            try:
                                if getattr(annot, "Subtype", None) != PdfName.Widget:
                                    continue
                                rect = annot.Rect
                                if not rect or len(rect) != 4:
                                    continue
                                x0, y0, x1, y1 = [float(v) for v in rect]
                                h = max(1.0, y1 - y0)
                                val = None
                                if getattr(annot, "V", None) is not None:
                                    raw = annot.V
                                    try:
                                        val = raw.to_unicode() if hasattr(raw, "to_unicode") else str(raw)
                                    except Exception:
                                        val = str(raw)
                                if val is None:
                                    continue
                                val = str(val).strip().strip("()")
                                font_size = max(8, min(14, h * 0.6))
                                c.setFont("Helvetica", font_size)
                                y_baseline = y0 + max(2, (h - font_size) * 0.75)
                                c.drawString(x0 + 2, y_baseline, val)
                            except Exception:
                                continue
                    c.showPage()
                c.save()

                # Merge overlay and remove form fields
                overlay_pdf = PdfReader(tmp_overlay_path)
                for i, page in enumerate(pages):
                    try:
                        if i < len(overlay_pdf.pages):
                            PageMerge(page).add(overlay_pdf.pages[i]).render()
                        if hasattr(page, "Annots"):
                            try:
                                del page.Annots
                            except Exception:
                                page.Annots = None
                    except Exception:
                        continue

                try:
                    if pdf.Root and getattr(pdf.Root, "AcroForm", None):
                        try:
                            del pdf.Root.AcroForm
                        except Exception:
                            pdf.Root.AcroForm = None
                except Exception:
                    pass

                PdfWriter().write(output_pdf, pdf)
                try:
                    os.remove(tmp_overlay_path)
                except Exception:
                    pass
                return True
            except Exception as e:
                log(_ts() + f"  [WARN] Flatten failed ({e}); uploading original (might appear blank).")
                return False
        
        # Step 1: Fill and lock
        # Try multiple field name variations for English and Spanish templates
        field_values = {
            "Client name print": client_name,
            "Client Name Print": client_name,
            "Nombre del Cliente": client_name,  # Spanish: Client Name
            "Nombre": client_name,  # Spanish: Name
            "Date": date,
            "Fecha": date  # Spanish: Date
        }
        if not fill_pdf_locked(template_path, output_path, field_values, log):
            return False
        
        # Step 2: Flatten
        fd, tmp_flat = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        flattened_ok = flatten_pdf_preserving_values(output_path, tmp_flat, log)
        if flattened_ok:
            import shutil
            shutil.move(tmp_flat, output_path)
        else:
            try:
                os.remove(tmp_flat)
            except:
                pass
        
        return True
    except Exception as e:
        log(_ts() + f"[PDF][ERR] Failed: {e}")
        import traceback
        log(traceback.format_exc())
        return False


# ===================== MAIN GUI =====================

class ConsentBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Consent Form Bot - Version 3.1.0, Last Updated 12/04/2025")
        self.root.geometry("660x650")
        
        # Shared Variables (for both tabs)
        self.excel_path = tk.StringVar()
        self.col_client_id = tk.StringVar(value="A")
        self.col_last_name = tk.StringVar(value="B")
        self.col_first_name = tk.StringVar(value="C")
        self.col_dob = tk.StringVar(value="D")
        self.col_counselor = tk.StringVar(value="E")  # Counselor column for IPS detection
        
        # Extractor-specific variables
        self.pn_username = tk.StringVar()
        self.pn_password = tk.StringVar()
        self.pn_url = tk.StringVar(value=PN_DEFAULT_URL)
        
        # Set default template paths
        # ISWS templates
        default_isws_en = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\_docs\File Templates\8 Consent and NPP - AS OF 04-07-2022.pdf"
        default_isws_es = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\_docs\File Templates\9 Consent and NPP Spanish AS OF 04-07- 22.pdf"
        
        # IPS templates
        default_ips_en = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\_docs\File Templates\IPS Welcome Letter English  - Consent and NPP Included - finalized.pdf"
        default_ips_es = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\_docs\File Templates\IPS Welcome Letter Spanish - Consent and NPP Included.pdf"
        
        self.en_template = tk.StringVar(value=default_isws_en if os.path.exists(default_isws_en) else "")
        self.es_template = tk.StringVar(value=default_isws_es if os.path.exists(default_isws_es) else "")
        self.ips_en_template = tk.StringVar(value=default_ips_en if os.path.exists(default_ips_en) else "")
        self.ips_es_template = tk.StringVar(value=default_ips_es if os.path.exists(default_ips_es) else "")
        
        # Extractor output locations (separate for PDFs and Excel logs)
        default_output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Consent form bot output")
        self.extractor_pdf_output_dir = tk.StringVar(value=default_output_dir)  # For PDF files
        self.extractor_excel_output_dir = tk.StringVar(value=default_output_dir)  # For Excel logs
        
        # Uploader-specific variables (ISWS)
        self.tn_username = tk.StringVar()
        self.tn_password = tk.StringVar()
        self.uploader_excel_path = tk.StringVar()
        self.uploader_pdf_folder = tk.StringVar()
        self.uploader_output_dir = tk.StringVar(value=default_output_dir)
        
        # IPS Uploader-specific variables
        self.ips_tn_username = tk.StringVar()
        self.ips_tn_password = tk.StringVar()
        self.ips_uploader_excel_path = tk.StringVar()
        self.ips_uploader_pdf_folder = tk.StringVar()
        
        self.ips_uploader_output_dir = tk.StringVar(value=default_output_dir)
        
        # User management (must be initialized before _build_ui())
        self.penelope_users_file = Path(__file__).parent / "consent_bot_penelope_users.json"
        self.penelope_users = {}  # Dictionary: {"name": {"username": "...", "password": "...", "url": "..."}}
        self.load_penelope_users()
        
        self.therapynotes_users_file = Path(__file__).parent / "consent_bot_therapynotes_users.json"
        self.therapynotes_users = {}  # Dictionary: {"name": {"username": "...", "password": "..."}}
        self.load_therapynotes_users()
        
        # IPS TherapyNotes users (separate from ISWS)
        self.ips_therapynotes_users_file = Path(__file__).parent / "consent_bot_ips_therapynotes_users.json"
        self.ips_therapynotes_users = {}  # Dictionary: {"name": {"username": "...", "password": "..."}}
        self.load_ips_therapynotes_users()
        
        # Setup GUI
        self._build_ui()
        
        # Bot state
        self.is_running = False
        self.stop_flag = threading.Event()
    
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
    
    def load_ips_therapynotes_users(self):
        """Load IPS TherapyNotes users from JSON file"""
        try:
            if self.ips_therapynotes_users_file.exists():
                with open(self.ips_therapynotes_users_file, 'r') as f:
                    self.ips_therapynotes_users = json.load(f)
            else:
                self.ips_therapynotes_users = {}
                self.save_ips_therapynotes_users()
        except Exception as e:
            self.ips_therapynotes_users = {}
    
    def save_ips_therapynotes_users(self):
        """Save IPS TherapyNotes users to JSON file"""
        try:
            with open(self.ips_therapynotes_users_file, 'w') as f:
                json.dump(self.ips_therapynotes_users, f, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save IPS TherapyNotes users:\n{e}")
            return False

    def _create_scrollable_frame(self, parent):
        """Create a scrollable frame with Canvas and Scrollbar"""
        # Create Canvas with Scrollbar
        canvas = tk.Canvas(parent, bg="#ffffff")
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#ffffff")
        
        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel scrolling to canvas and all child widgets
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except:
                pass
        
        def _on_scroll_up(event):
            try:
                canvas.yview_scroll(-1, "units")
            except:
                pass
        
        def _on_scroll_down(event):
            try:
                canvas.yview_scroll(1, "units")
            except:
                pass
        
        # Bind to canvas
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_scroll_up)
        canvas.bind("<Button-5>", _on_scroll_down)
        
        # Also bind to all child widgets recursively
        def bind_to_children(widget):
            for child in widget.winfo_children():
                try:
                    child.bind("<MouseWheel>", _on_mousewheel)
                    child.bind("<Button-4>", _on_scroll_up)
                    child.bind("<Button-5>", _on_scroll_down)
                    bind_to_children(child)
                except:
                    pass
        
        # Bind to scrollable frame and all its children
        bind_to_children(scrollable_frame)
        
        # Update scroll region when canvas is configured
        def on_canvas_configure(event):
            # Update the scroll region to match the scrollable frame's size
            canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", on_canvas_configure)
        
        return scrollable_frame
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=MAROON, height=50)
        header.pack(fill="x")
        tk.Label(header, text=APP_TITLE, bg=MAROON, fg="white",
                font=("Arial", 16, "bold")).pack(pady=10)
        
        # Create Notebook (tabbed interface)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create tabs
        self.extractor_tab = tk.Frame(notebook)
        self.uploader_tab = tk.Frame(notebook)
        self.ips_uploader_tab = tk.Frame(notebook)
        
        notebook.add(self.extractor_tab, text="Extractor")
        notebook.add(self.uploader_tab, text="ISWS Uploader")
        notebook.add(self.ips_uploader_tab, text="IPS Uploader")
        
        # Build tab contents
        self._build_extractor_tab()
        self._build_uploader_tab()
        self._build_ips_uploader_tab()
    
    def _build_extractor_tab(self):
        # Create scrollable frame for extractor
        scrollable_frame = self._create_scrollable_frame(self.extractor_tab)
        
        # Main container for extractor
        main_frame = tk.Frame(scrollable_frame)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        main_frame.configure(width=600)
        
        # Credentials section
        cred_frame = tk.LabelFrame(main_frame, text="Penelope Credentials", font=("Arial", 10, "bold"))
        cred_frame.pack(fill="x", pady=3)
        cred_frame.columnconfigure(1, weight=1)
        
        # User Selection Row
        tk.Label(cred_frame, text="Saved User:", font=("Arial", 10)).grid(row=0, column=0, sticky="e", padx=5, pady=5)
        
        # User Selection Dropdown
        self.penelope_user_dropdown = ttk.Combobox(cred_frame, font=("Arial", 9), width=25, state="readonly")
        self.penelope_user_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.penelope_user_dropdown.bind("<<ComboboxSelected>>", self._on_penelope_user_selected)
        self._update_penelope_user_dropdown()
        
        # Add User button
        tk.Button(cred_frame, text="Add User", command=self._add_penelope_user,
                 bg=MAROON, fg="white", font=("Arial", 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=0, column=2, padx=5, pady=5)
        
        # Update User button
        tk.Button(cred_frame, text="Update User", command=self._update_penelope_user,
                 bg="#666666", fg="white", font=("Arial", 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=0, column=3, padx=5, pady=5)
        
        # Credentials fields
        tk.Label(cred_frame, text="URL:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(cred_frame, textvariable=self.pn_url).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        tk.Label(cred_frame, text="Username:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(cred_frame, textvariable=self.pn_username).grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        tk.Label(cred_frame, text="Password:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(cred_frame, textvariable=self.pn_password, show="*").grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        
        # Files section
        files_frame = tk.LabelFrame(main_frame, text="Templates", font=("Arial", 10, "bold"))
        files_frame.pack(fill="x", pady=3)
        files_frame.columnconfigure(2, weight=1)
        
        tk.Label(files_frame, text="Excel/CSV:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        tk.Button(files_frame, text="Select File", command=self._pick_excel).grid(row=0, column=1, padx=5, pady=5)
        self.excel_label = tk.Label(files_frame, text="No file selected")
        self.excel_label.grid(row=0, column=2, sticky="w", padx=5, pady=5)
        
        # ISWS Templates
        tk.Label(files_frame, text="ISWS English Template:", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky="e", padx=5, pady=5)
        tk.Button(files_frame, text="Select", command=self._pick_en_template).grid(row=1, column=1, padx=5, pady=5)
        default_en_display = os.path.basename(self.en_template.get()) if self.en_template.get() else "No file selected"
        self.en_label = tk.Label(files_frame, text=default_en_display)
        self.en_label.grid(row=1, column=2, sticky="w", padx=5, pady=5)
        
        tk.Label(files_frame, text="ISWS Spanish Template:", font=("Arial", 9, "bold")).grid(row=2, column=0, sticky="e", padx=5, pady=5)
        tk.Button(files_frame, text="Select", command=self._pick_es_template).grid(row=2, column=1, padx=5, pady=5)
        default_es_display = os.path.basename(self.es_template.get()) if self.es_template.get() else "No file selected"
        self.es_label = tk.Label(files_frame, text=default_es_display)
        self.es_label.grid(row=2, column=2, sticky="w", padx=5, pady=5)
        
        # IPS Templates
        tk.Label(files_frame, text="IPS English Template:", font=("Arial", 9, "bold")).grid(row=3, column=0, sticky="e", padx=5, pady=5)
        tk.Button(files_frame, text="Select", command=self._pick_ips_en_template).grid(row=3, column=1, padx=5, pady=5)
        default_ips_en_display = os.path.basename(self.ips_en_template.get()) if self.ips_en_template.get() else "No file selected"
        self.ips_en_label = tk.Label(files_frame, text=default_ips_en_display)
        self.ips_en_label.grid(row=3, column=2, sticky="w", padx=5, pady=5)
        
        tk.Label(files_frame, text="IPS Spanish Template:", font=("Arial", 9, "bold")).grid(row=4, column=0, sticky="e", padx=5, pady=5)
        tk.Button(files_frame, text="Select", command=self._pick_ips_es_template).grid(row=4, column=1, padx=5, pady=5)
        default_ips_es_display = os.path.basename(self.ips_es_template.get()) if self.ips_es_template.get() else "No file selected"
        self.ips_es_label = tk.Label(files_frame, text=default_ips_es_display)
        self.ips_es_label.grid(row=4, column=2, sticky="w", padx=5, pady=5)
        
        # PDF Output location section
        pdf_output_frame = tk.LabelFrame(main_frame, text="PDF Output Location", font=("Arial", 10, "bold"))
        pdf_output_frame.pack(fill="x", pady=3)
        pdf_output_frame.columnconfigure(1, weight=1)
        
        tk.Label(pdf_output_frame, text="PDF Directory:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(pdf_output_frame, textvariable=self.extractor_pdf_output_dir, width=50).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        tk.Button(pdf_output_frame, text="Browse", command=self._pick_extractor_pdf_output_dir).grid(row=0, column=2, padx=5, pady=5)
        
        # Excel Log Output location section
        excel_output_frame = tk.LabelFrame(main_frame, text="Excel Log Output Location", font=("Arial", 10, "bold"))
        excel_output_frame.pack(fill="x", pady=3)
        excel_output_frame.columnconfigure(1, weight=1)
        
        tk.Label(excel_output_frame, text="Excel Log Directory:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(excel_output_frame, textvariable=self.extractor_excel_output_dir, width=50).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        tk.Button(excel_output_frame, text="Browse", command=self._pick_extractor_excel_output_dir).grid(row=0, column=2, padx=5, pady=5)
        
        # Column mapping section
        mapping_frame = tk.LabelFrame(main_frame, text="Column Mapping", font=("Arial", 10, "bold"))
        mapping_frame.pack(fill="x", pady=3)
        
        tk.Label(mapping_frame, text="Client ID:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        tk.Entry(mapping_frame, textvariable=self.col_client_id, width=5).grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(mapping_frame, text="Last Name:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        tk.Entry(mapping_frame, textvariable=self.col_last_name, width=5).grid(row=0, column=3, padx=5, pady=2)
        
        tk.Label(mapping_frame, text="First Name:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        tk.Entry(mapping_frame, textvariable=self.col_first_name, width=5).grid(row=1, column=1, padx=5, pady=2)
        
        tk.Label(mapping_frame, text="DOB:").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        tk.Entry(mapping_frame, textvariable=self.col_dob, width=5).grid(row=1, column=3, padx=5, pady=2)
        
        tk.Label(mapping_frame, text="Counselor:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        tk.Entry(mapping_frame, textvariable=self.col_counselor, width=5).grid(row=2, column=1, padx=5, pady=2)
        
        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=5)
        
        self.start_btn = tk.Button(btn_frame, text="Start", command=self._start_bot, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="Stop", command=self._stop_bot, state="disabled", bg="#f44336", fg="white", font=("Arial", 12))
        self.stop_btn.pack(side="left", padx=5)
        
        # Log area
        log_frame = tk.LabelFrame(main_frame, text="Log", font=("Arial", 10, "bold"))
        log_frame.pack(fill="both", expand=True, pady=3)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Courier", 9))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def _pick_excel(self):
        f = filedialog.askopenfilename(filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"), ("All files", "*.*")])
        if f:
            self.excel_path.set(f)
            self.excel_label.config(text=os.path.basename(f))

    def _pick_en_template(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.en_template.set(f)
            self.en_label.config(text=os.path.basename(f))

    def _pick_es_template(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.es_template.set(f)
            self.es_label.config(text=os.path.basename(f))
    
    def _pick_ips_en_template(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.ips_en_template.set(f)
            self.ips_en_label.config(text=os.path.basename(f))
    
    def _pick_ips_es_template(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.ips_es_template.set(f)
            self.ips_es_label.config(text=os.path.basename(f))
    
    def _pick_extractor_pdf_output_dir(self):
        d = filedialog.askdirectory(initialdir=self.extractor_pdf_output_dir.get())
        if d:
            self.extractor_pdf_output_dir.set(d)
    
    def _pick_extractor_excel_output_dir(self):
        d = filedialog.askdirectory(initialdir=self.extractor_excel_output_dir.get())
        if d:
            self.extractor_excel_output_dir.set(d)
    
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
            self.pn_username.set(user_data.get('username', ''))
            self.pn_password.set(user_data.get('password', ''))
            self.pn_url.set(user_data.get('url', PN_DEFAULT_URL))
    
    def _add_penelope_user(self):
        """Add a new Penelope user to saved users"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Penelope User - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("450x280")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="User Name:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(20, 5))
        name_entry = tk.Entry(dialog, font=("Arial", 10), width=35)
        name_entry.pack(pady=(0, 10))
        name_entry.focus()
        
        tk.Label(dialog, text="Username:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(0, 5))
        username_entry = tk.Entry(dialog, font=("Arial", 10), width=35)
        username_entry.pack(pady=(0, 10))
        
        tk.Label(dialog, text="Password:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(0, 5))
        password_entry = tk.Entry(dialog, font=("Arial", 10), width=35, show="•")
        password_entry.pack(pady=(0, 10))
        
        tk.Label(dialog, text="Penelope URL (optional):", font=("Arial", 10), bg="#f0f0f0").pack(pady=(0, 5))
        url_entry = tk.Entry(dialog, font=("Arial", 10), width=35)
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
                 bg=MAROON, fg="white", font=("Arial", 10),
                 padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg="#666666", fg="white", font=("Arial", 10),
                 padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
    
    def _update_penelope_user(self):
        """Update credentials for selected Penelope user"""
        selected_user = self.penelope_user_dropdown.get()
        if not selected_user or selected_user not in self.penelope_users:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown")
            return
        
        username = self.pn_username.get().strip()
        password = self.pn_password.get().strip()
        url = self.pn_url.get().strip() or PN_DEFAULT_URL
        
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
            self.tn_username.set(user_data.get('username', ''))
            self.tn_password.set(user_data.get('password', ''))
    
    def _add_therapynotes_user(self):
        """Add a new TherapyNotes user to saved users"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add TherapyNotes User - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("450x220")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="User Name:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(20, 5))
        name_entry = tk.Entry(dialog, font=("Arial", 10), width=35)
        name_entry.pack(pady=(0, 10))
        name_entry.focus()
        
        tk.Label(dialog, text="Username:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(0, 5))
        username_entry = tk.Entry(dialog, font=("Arial", 10), width=35)
        username_entry.pack(pady=(0, 10))
        
        tk.Label(dialog, text="Password:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(0, 5))
        password_entry = tk.Entry(dialog, font=("Arial", 10), width=35, show="•")
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
                 bg=MAROON, fg="white", font=("Arial", 10),
                 padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg="#666666", fg="white", font=("Arial", 10),
                 padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
    
    def _update_therapynotes_user(self):
        """Update credentials for selected TherapyNotes user"""
        selected_user = self.therapynotes_user_dropdown.get()
        if not selected_user or selected_user not in self.therapynotes_users:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown")
            return
        
        username = self.tn_username.get().strip()
        password = self.tn_password.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Invalid Input", "Username and password are required")
            return
        
        self.therapynotes_users[selected_user] = {
            'username': username,
            'password': password
        }
        self.save_therapynotes_users()
        messagebox.showinfo("Success", f"Credentials updated for '{selected_user}'")
    
    def _update_ips_therapynotes_user_dropdown(self):
        """Update the IPS TherapyNotes user dropdown with current users"""
        if hasattr(self, 'ips_therapynotes_user_dropdown'):
            user_names = sorted(self.ips_therapynotes_users.keys())
            if user_names:
                self.ips_therapynotes_user_dropdown['values'] = user_names
            else:
                self.ips_therapynotes_user_dropdown['values'] = []
    
    def _on_ips_therapynotes_user_selected(self, event=None):
        """Handle IPS TherapyNotes user selection from dropdown"""
        selected_user = self.ips_therapynotes_user_dropdown.get()
        if selected_user and selected_user in self.ips_therapynotes_users:
            user_data = self.ips_therapynotes_users[selected_user]
            self.ips_tn_username.set(user_data.get('username', ''))
            self.ips_tn_password.set(user_data.get('password', ''))
    
    def _add_ips_therapynotes_user(self):
        """Add a new IPS TherapyNotes user to saved users"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add IPS TherapyNotes User - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("450x220")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="User Name:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(20, 5))
        name_entry = tk.Entry(dialog, font=("Arial", 10), width=35)
        name_entry.pack(pady=(0, 10))
        name_entry.focus()
        
        tk.Label(dialog, text="Username:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(0, 5))
        username_entry = tk.Entry(dialog, font=("Arial", 10), width=35)
        username_entry.pack(pady=(0, 10))
        
        tk.Label(dialog, text="Password:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(0, 5))
        password_entry = tk.Entry(dialog, font=("Arial", 10), width=35, show="•")
        password_entry.pack(pady=(0, 15))
        
        def save_user():
            name = name_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            if not name or not username or not password:
                messagebox.showwarning("Invalid Input", "User Name, Username, and Password are required")
                return
            
            if name in self.ips_therapynotes_users:
                if not messagebox.askyesno("User Exists", f"User '{name}' already exists. Overwrite?"):
                    return
            
            self.ips_therapynotes_users[name] = {
                'username': username,
                'password': password
            }
            self.save_ips_therapynotes_users()
            self._update_ips_therapynotes_user_dropdown()
            dialog.destroy()
            messagebox.showinfo("Success", f"User '{name}' added successfully")
        
        button_frame = tk.Frame(dialog, bg="#f0f0f0")
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Save", command=save_user,
                 bg=MAROON, fg="white", font=("Arial", 10),
                 padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg="#666666", fg="white", font=("Arial", 10),
                 padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
    
    def _update_ips_therapynotes_user(self):
        """Update credentials for selected IPS TherapyNotes user"""
        selected_user = self.ips_therapynotes_user_dropdown.get()
        if not selected_user or selected_user not in self.ips_therapynotes_users:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown")
            return
        
        username = self.ips_tn_username.get().strip()
        password = self.ips_tn_password.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Invalid Input", "Username and password are required")
            return
        
        self.ips_therapynotes_users[selected_user] = {
            'username': username,
            'password': password
        }
        self.save_ips_therapynotes_users()
        messagebox.showinfo("Success", f"Credentials updated for '{selected_user}'")
    
    def _extract_date_from_pdf(self, pdf_path):
        """Extract date from PDF file using PDF form fields or text extraction"""
        try:
            # First try to read from PDF form fields
            try:
                from pdfrw import PdfReader
                pdf = PdfReader(pdf_path)
                
                # Look for date fields in the PDF
                date_keywords = ['date', 'fecha']
                for page in pdf.pages:
                    annots = getattr(page, "Annots", None)
                    if not annots:
                        continue
                    for annot in annots:
                        if getattr(annot, "Subtype", None).name == "Widget" and getattr(annot, "T", None):
                            field_name = str(annot.T).strip('()').lower()
                            if any(keyword in field_name for keyword in date_keywords):
                                try:
                                    value = annot.get("/V")
                                    if value:
                                        value_str = str(value).strip('()')
                                        # Try to parse the date
                                        date_formats = ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%y", "%m-%d-%y"]
                                        for fmt in date_formats:
                                            try:
                                                date_obj = DT.strptime(value_str, fmt)
                                                return date_obj.strftime("%m/%d/%Y")
                                            except:
                                                continue
                                        # If parsing fails, return as-is if it looks like a date
                                        if "/" in value_str or "-" in value_str:
                                            return value_str
                                except:
                                    pass
            except Exception as e:
                pass  # Fall through to text extraction
            
            # Try text extraction using pdfplumber or similar
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            # Look for date patterns in the text
                            date_patterns = [
                                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # MM/DD/YYYY or MM-DD-YYYY
                                r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',     # YYYY/MM/DD or YYYY-MM-DD
                            ]
                            for pattern in date_patterns:
                                matches = re.findall(pattern, text)
                                if matches:
                                    # Try to parse the first date found
                                    date_str = matches[0]
                                    date_formats = ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%y", "%m-%d-%y"]
                                    for fmt in date_formats:
                                        try:
                                            date_obj = DT.strptime(date_str, fmt)
                                            return date_obj.strftime("%m/%d/%Y")
                                        except:
                                            continue
            except Exception as e:
                pass  # Could not extract from PDF
            
            return None  # No date found
        except Exception as e:
            return None

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def _start_bot(self):
        if not self.excel_path.get() or not self.en_template.get() or not self.es_template.get() or not self.ips_en_template.get() or not self.ips_es_template.get():
            messagebox.showerror("Error", "Please select Excel file and all 4 PDF templates (ISWS English, ISWS Spanish, IPS English, IPS Spanish)")
            return
        
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.is_running = True
        self.stop_flag.clear()
        
        # Start bot in thread
        thread = threading.Thread(target=self._run_bot, daemon=True)
        thread.start()

    def _stop_bot(self):
        self.log(_ts() + "[BOT] Stopping...")
        self.is_running = False
        self.stop_flag.set()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _run_bot(self):
        try:
            self.log(_ts() + "[BOT] Starting...")
            
            # Load Excel/CSV
            self.log(_ts() + f"[BOT] Loading {self.excel_path.get()}")
            try:
                if self.excel_path.get().endswith('.csv'):
                    df = pd.read_csv(self.excel_path.get())
                else:
                    df = pd.read_excel(self.excel_path.get())
            except PermissionError as e:
                error_msg = f"[BOT][ERR] Permission denied: Cannot read the Excel file.\n"
                error_msg += "The file may be open in Excel or another program.\n"
                error_msg += "Please close the file and try again."
                self.log(_ts() + error_msg)
                messagebox.showerror("Permission Error", 
                    "Cannot read the Excel file. The file may be:\n"
                    "• Open in Microsoft Excel\n"
                    "• Locked by OneDrive sync\n"
                    "• Being used by another program\n\n"
                    "Please close the file and try again.")
                return
            except Exception as e:
                error_msg = f"[BOT][ERR] Failed to load Excel/CSV file: {e}"
                self.log(_ts() + error_msg)
                messagebox.showerror("File Error", f"Failed to load the Excel/CSV file:\n{e}")
                return
            
            # Helper function to convert column letter to index
            def col_letter_to_index(letter):
                """Convert column letter (A, B, C) to index (0, 1, 2)"""
                letter = letter.upper().strip()
                index = ord(letter) - ord('A')
                return index
            
            # Get column mappings
            col_id_idx = col_letter_to_index(self.col_client_id.get())
            col_last_idx = col_letter_to_index(self.col_last_name.get())
            col_first_idx = col_letter_to_index(self.col_first_name.get())
            col_dob_idx = col_letter_to_index(self.col_dob.get())
            col_counselor_idx = col_letter_to_index(self.col_counselor.get())
            
            # Get data from specified columns
            client_ids = df.iloc[:, col_id_idx].astype(str).tolist()
            last_names = df.iloc[:, col_last_idx].astype(str).tolist() if col_last_idx < len(df.columns) else [""] * len(client_ids)
            first_names = df.iloc[:, col_first_idx].astype(str).tolist() if col_first_idx < len(df.columns) else [""] * len(client_ids)
            dobs = df.iloc[:, col_dob_idx].astype(str).tolist() if col_dob_idx < len(df.columns) else [""] * len(client_ids)
            counselors = df.iloc[:, col_counselor_idx].astype(str).tolist() if col_counselor_idx < len(df.columns) else [""] * len(client_ids)
            
            self.log(_ts() + f"[BOT] Found {len(client_ids)} clients")
            self.log(_ts() + f"[BOT] Using columns: Client ID={self.col_client_id.get()}, Last={self.col_last_name.get()}, First={self.col_first_name.get()}, DOB={self.col_dob.get()}, Counselor={self.col_counselor.get()}")
            
            # Initialize Penelope client
            auth = PNAuth(
                url=self.pn_url.get(),
                username=self.pn_username.get(),
                password=self.pn_password.get()
            )
            pn = PNClient(auth, self.log)
            
            # Start browser and login
            pn.start()
            if not pn.login():
                self.log(_ts() + "[BOT][ERR] Login failed")
                return
            
            # Go to Search page (CRITICAL - must happen before processing clients)
            self.log(_ts() + "[NAV] Opening Search page...")
            if not pn.go_to_search():
                self.log(_ts() + "[NAV][WARN] Could not open Search page; bot will attempt to continue")
            
            # Process each client
            # Use PDF output directory for saving PDFs
            pdf_output_dir = self.extractor_pdf_output_dir.get()
            if not pdf_output_dir:
                pdf_output_dir = ensure_output_dir()
            os.makedirs(pdf_output_dir, exist_ok=True)
            
            # Use Excel output directory for saving Excel logs
            excel_output_dir = self.extractor_excel_output_dir.get()
            if not excel_output_dir:
                excel_output_dir = ensure_output_dir()
            os.makedirs(excel_output_dir, exist_ok=True)
            
            # Track results for Excel log
            log_rows = []
            
            for i, client_id in enumerate(client_ids):
                if not self.is_running:
                    break
                
                client_last = last_names[i] if i < len(last_names) else ""
                client_first = first_names[i] if i < len(first_names) else ""
                client_dob = dobs[i] if i < len(dobs) else ""
                client_counselor = counselors[i] if i < len(counselors) else ""
                
                # Check if this is an IPS client (counselor contains "IPS" - case insensitive)
                # Format in Excel: "CounselorName IPS" or "CounselorName IPS - asap"
                counselor_upper = str(client_counselor).upper().strip() if client_counselor else ""
                is_ips_client = False
                if counselor_upper:
                    # Check if "IPS" appears in the counselor name (e.g., "Michelle Santana IPS", "Cynthia Hernandez IPS")
                    is_ips_client = " IPS" in counselor_upper or counselor_upper.endswith("IPS")
                
                # Log counselor info for debugging
                if client_counselor:
                    self.log(_ts() + f"[BOT] Counselor: '{client_counselor}' -> IPS: {is_ips_client}")
                
                self.log(_ts() + f"[BOT] Processing client {i+1}/{len(client_ids)}: {client_id} ({client_first} {client_last})" + (f" [IPS]" if is_ips_client else ""))
                
                # Search for client - use exact methods from counselor bot
                if not pn.enter_individual_id_and_go(client_id):
                    self.log(_ts() + f"[BOT][WARN] Failed to search for client {client_id}")
                    continue
                
                # Click the client's name to navigate to profile
                if not pn.click_first_result_name(first_name=client_first, last_name=client_last):
                    self.log(_ts() + f"[BOT][WARN] Failed to click client name for {client_id}")
                    continue
                
                # Extract data
                data = pn.extract_client_data()
                if not data:
                    self.log(_ts() + f"[BOT][WARN] No data extracted for {client_id}")
                    continue
                
                # Select template based on ISWS/IPS and language
                language = data.get("language", "English")
                if is_ips_client:
                    # IPS client - use IPS templates
                    if language == "Spanish":
                        template = self.ips_es_template.get()
                        self.log(_ts() + "[BOT] Using IPS Spanish template")
                    else:
                        template = self.ips_en_template.get()
                        self.log(_ts() + "[BOT] Using IPS English template")
                else:
                    # ISWS client - use ISWS templates
                    if language == "Spanish":
                        template = self.es_template.get()
                        self.log(_ts() + "[BOT] Using ISWS Spanish template")
                    else:
                        template = self.en_template.get()
                        self.log(_ts() + "[BOT] Using ISWS English template")
                
                # Create output filename in format "First LAST Consent NPP.pdf"
                date = data.get("date", DT.now().strftime("%m/%d/%Y"))
                
                # Extract first and last name from client_name or use separate fields
                if client_first and client_last:
                    base_filename = f"{client_first.strip()} {client_last.strip()} Consent NPP.pdf"
                elif "client_name" in data:
                    # Try to parse client name if we have it
                    name_parts = data.get("client_name", "Unknown").split()
                    if len(name_parts) >= 2:
                        base_filename = f"{name_parts[0]} {' '.join(name_parts[1:])} Consent NPP.pdf"
                    else:
                        base_filename = sanitize_filename(data.get("client_name", "Unknown")) + " Consent NPP.pdf"
                else:
                    base_filename = "Unknown Client Consent NPP.pdf"
                
                # Add IPS prefix if this is an IPS client
                if is_ips_client:
                    pdf_filename = f"IPS {base_filename}"
                    self.log(_ts() + f"[BOT] Marking as IPS client - adding IPS prefix to filename")
                else:
                    pdf_filename = base_filename
                
                filename = sanitize_filename(pdf_filename)
                output_path = os.path.join(pdf_output_dir, filename)
                
                # Get client name for PDF filling
                client_name = data.get("client_name", "Unknown Client")
                
                # Fill and flatten PDF
                success = False
                if fill_and_flatten_pdf(template, output_path, client_name, date, self.log):
                    self.log(_ts() + f"[BOT] Created: {filename}")
                    success = True
                else:
                    self.log(_ts() + f"[BOT][WARN] Failed to create PDF for {client_id}")
                
                # Get DOB for this client (from the input Excel)
                client_dob = dobs[i] if i < len(dobs) else ""
                
                # Add to log
                log_rows.append({
                    'Client ID': client_id,
                    'Client Name': f"{client_first} {client_last}".strip(),
                    'DOB': client_dob,  # Include DOB from input Excel
                    'Counselor': client_counselor,  # Include counselor from input Excel
                    'IPS Client': 'Yes' if is_ips_client else 'No',  # Mark IPS status
                    'Language': language,
                    'Date': date,
                    'PDF Created': 'Yes' if success else 'No',
                    'PDF Filename': filename if success else ''
                })
                
                # Click search button to return to search for next client (skip for last client)
                if i < len(client_ids) - 1:
                    self.log(_ts() + "[BOT] Returning to search for next client...")
                    try:
                        from selenium.webdriver.common.by import By
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        
                        d = pn.driver
                        d.switch_to.default_content()
                        
                        # Try each frame to find navSearch button
                        frames = d.find_elements(By.TAG_NAME, "frame") + d.find_elements(By.TAG_NAME, "iframe")
                        for fr in frames:
                            try:
                                d.switch_to.default_content()
                                d.switch_to.frame(fr)
                                
                                try:
                                    search_btn = d.find_element(By.ID, "navSearch")
                                    if search_btn and search_btn.is_displayed():
                                        search_btn.click()
                                        self.log(_ts() + "[BOT] Clicked search button")
                                        break
                                except:
                                    continue
                            except:
                                continue
                        
                        d.switch_to.default_content()
                    except Exception as e:
                        self.log(_ts() + f"[BOT][WARN] Could not click search button: {e}")
            
            # Generate Excel log
            if log_rows:
                try:
                    timestamp = DT.now().strftime("%Y%m%d_%H%M%S")
                    log_filename = f"Consent_Extractor_Log_{timestamp}.xlsx"
                    log_path = os.path.join(excel_output_dir, log_filename)
                    
                    df = pd.DataFrame(log_rows)
                    df.to_excel(log_path, index=False)
                    self.log(_ts() + f"[BOT] Excel log saved: {log_path}")
                except Exception as e:
                    self.log(_ts() + f"[BOT][WARN] Failed to save Excel log: {e}")
            
            self.log(_ts() + "[BOT] Complete!")
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.is_running = False
            
        except Exception as e:
            self.log(_ts() + f"[BOT][ERR] {e}")
            import traceback
            self.log(traceback.format_exc())
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.is_running = False
    
    def _build_uploader_tab(self):
        """Build the ISWS Uploader tab"""
        # Create scrollable frame for uploader
        scrollable_frame = self._create_scrollable_frame(self.uploader_tab)
        
        # Main container for uploader
        main_frame = tk.Frame(scrollable_frame)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        main_frame.configure(width=600)
        
        # TherapyNotes Credentials section
        cred_frame = tk.LabelFrame(main_frame, text="TherapyNotes ISWS Credentials", font=("Arial", 10, "bold"))
        cred_frame.pack(fill="x", pady=3)
        cred_frame.columnconfigure(1, weight=1)
        
        # User Selection Row
        tk.Label(cred_frame, text="Saved User:", font=("Arial", 10)).grid(row=0, column=0, sticky="e", padx=5, pady=5)
        
        # User Selection Dropdown
        self.therapynotes_user_dropdown = ttk.Combobox(cred_frame, font=("Arial", 9), width=25, state="readonly")
        self.therapynotes_user_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.therapynotes_user_dropdown.bind("<<ComboboxSelected>>", self._on_therapynotes_user_selected)
        self._update_therapynotes_user_dropdown()
        
        # Add User button
        tk.Button(cred_frame, text="Add User", command=self._add_therapynotes_user,
                 bg=MAROON, fg="white", font=("Arial", 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=0, column=2, padx=5, pady=5)
        
        # Update User button
        tk.Button(cred_frame, text="Update User", command=self._update_therapynotes_user,
                 bg="#666666", fg="white", font=("Arial", 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=0, column=3, padx=5, pady=5)
        
        # Credentials fields
        tk.Label(cred_frame, text="Username:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(cred_frame, textvariable=self.tn_username).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        tk.Label(cred_frame, text="Password:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(cred_frame, textvariable=self.tn_password, show="*").grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        # File Selection section
        files_frame = tk.LabelFrame(main_frame, text="File Selection", font=("Arial", 10, "bold"))
        files_frame.pack(fill="x", pady=3)
        files_frame.columnconfigure(2, weight=1)
        
        tk.Label(files_frame, text="Excel/CSV:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        tk.Button(files_frame, text="Select File", command=self._pick_uploader_excel).grid(row=0, column=1, padx=5, pady=5)
        self.uploader_excel_label = tk.Label(files_frame, text="No file selected")
        self.uploader_excel_label.grid(row=0, column=2, sticky="w", padx=5, pady=5)
        
        tk.Label(files_frame, text="PDF Folder:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        tk.Button(files_frame, text="Select Folder", command=self._pick_uploader_folder).grid(row=1, column=1, padx=5, pady=5)
        self.uploader_folder_label = tk.Label(files_frame, text="No folder selected")
        self.uploader_folder_label.grid(row=1, column=2, sticky="w", padx=5, pady=5)
        
        # Output location section
        output_frame = tk.LabelFrame(main_frame, text="Output Location (Excel Logs)", font=("Arial", 10, "bold"))
        output_frame.pack(fill="x", pady=3)
        output_frame.columnconfigure(1, weight=1)
        
        tk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(output_frame, textvariable=self.uploader_output_dir, width=50).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        tk.Button(output_frame, text="Browse", command=self._pick_uploader_output_dir).grid(row=0, column=2, padx=5, pady=5)
        
        # Column mapping section (for non-extractor log files)
        mapping_frame = tk.LabelFrame(main_frame, text="Column Mapping (for non-extractor log files)", font=("Arial", 10, "bold"))
        mapping_frame.pack(fill="x", pady=3)
        
        # Row 1: Full Name (if provided, will be used instead of separate First/Last)
        tk.Label(mapping_frame, text="Full Name:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.uploader_col_full_name = tk.StringVar(value="")
        tk.Entry(mapping_frame, textvariable=self.uploader_col_full_name, width=5).grid(row=0, column=1, padx=5, pady=2)
        tk.Label(mapping_frame, text="(optional - if filled, First/Last Name columns ignored)", font=("Arial", 8), fg="gray").grid(row=0, column=2, columnspan=4, sticky="w", padx=5, pady=2)
        
        # Row 2: Name and DOB columns
        tk.Label(mapping_frame, text="Last Name:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.uploader_col_last_name = tk.StringVar(value=self.col_last_name.get())
        tk.Entry(mapping_frame, textvariable=self.uploader_col_last_name, width=5).grid(row=1, column=1, padx=5, pady=2)
        
        tk.Label(mapping_frame, text="First Name:").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        self.uploader_col_first_name = tk.StringVar(value=self.col_first_name.get())
        tk.Entry(mapping_frame, textvariable=self.uploader_col_first_name, width=5).grid(row=1, column=3, padx=5, pady=2)
        
        tk.Label(mapping_frame, text="DOB:").grid(row=1, column=4, sticky="e", padx=5, pady=2)
        self.uploader_col_dob = tk.StringVar(value=self.col_dob.get())
        tk.Entry(mapping_frame, textvariable=self.uploader_col_dob, width=5).grid(row=1, column=5, padx=5, pady=2)
        
        # Row 3: Date and Counselor columns
        tk.Label(mapping_frame, text="Date:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.uploader_col_date = tk.StringVar(value="D")  # Default to column D
        tk.Entry(mapping_frame, textvariable=self.uploader_col_date, width=5).grid(row=2, column=1, padx=5, pady=2)
        
        tk.Label(mapping_frame, text="Counselor:").grid(row=2, column=2, sticky="e", padx=5, pady=2)
        self.uploader_col_counselor = tk.StringVar(value=self.col_counselor.get())
        tk.Entry(mapping_frame, textvariable=self.uploader_col_counselor, width=5).grid(row=2, column=3, padx=5, pady=2)
        
        info_text = "Note: If the file is an extractor log (has 'Client Name' column), column mapping is ignored."
        tk.Label(mapping_frame, text=info_text, justify="left", wraplength=600, font=("Arial", 8)).grid(row=3, column=0, columnspan=6, sticky="w", padx=5, pady=2)
        
        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=5)
        
        self.uploader_start_btn = tk.Button(btn_frame, text="Start Upload", command=self._start_uploader, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
        self.uploader_start_btn.pack(side="left", padx=5)
        
        self.uploader_stop_btn = tk.Button(btn_frame, text="Stop", command=self._stop_bot, state="disabled", bg="#f44336", fg="white", font=("Arial", 12))
        self.uploader_stop_btn.pack(side="left", padx=5)
        
        # Log area
        log_frame = tk.LabelFrame(main_frame, text="Uploader Log", font=("Arial", 10, "bold"))
        log_frame.pack(fill="both", expand=True, pady=3)
        
        self.uploader_log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Courier", 9))
        self.uploader_log_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def _pick_uploader_excel(self):
        f = filedialog.askopenfilename(filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"), ("All files", "*.*")])
        if f:
            self.uploader_excel_path.set(f)
            self.uploader_excel_label.config(text=os.path.basename(f))
    
    def _pick_uploader_folder(self):
        f = filedialog.askdirectory()
        if f:
            self.uploader_pdf_folder.set(f)
            self.uploader_folder_label.config(text=os.path.basename(f))
    
    def _pick_uploader_output_dir(self):
        d = filedialog.askdirectory(initialdir=self.uploader_output_dir.get())
        if d:
            self.uploader_output_dir.set(d)
    
    def _start_uploader(self):
        """Start the uploader bot"""
        if not self.uploader_excel_path.get():
            messagebox.showerror("Error", "Please select the Excel/CSV file in the Uploader tab")
            return
        if not self.uploader_pdf_folder.get():
            messagebox.showerror("Error", "Please select the PDF folder in the Uploader tab")
            return
        if not self.tn_username.get() or not self.tn_password.get():
            messagebox.showerror("Error", "Please enter TherapyNotes credentials")
            return
        
        self.uploader_start_btn.config(state="disabled")
        self.uploader_stop_btn.config(state="normal")
        self.is_running = True
        self.stop_flag.clear()
        
        # Start uploader in thread
        thread = threading.Thread(target=self._run_uploader, daemon=True)
        thread.start()
    
    def _run_uploader(self):
        """Run the uploader bot to upload PDFs to TherapyNotes ISWS"""
        try:
            import pandas as pd
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException
            import tempfile
            
            # Load Excel to get client names
            try:
                df = pd.read_excel(self.uploader_excel_path.get())
            except PermissionError as e:
                error_msg = f"[UPLOADER][ERR] Permission denied: Cannot read the Excel file.\n"
                error_msg += "The file may be open in Excel or another program.\n"
                error_msg += "Please close the file and try again."
                self.log_uploader(_ts() + error_msg)
                messagebox.showerror("Permission Error", 
                    "Cannot read the Excel file. The file may be:\n"
                    "• Open in Microsoft Excel\n"
                    "• Locked by OneDrive sync\n"
                    "• Being used by another program\n\n"
                    "Please close the file and try again.")
                return
            except Exception as e:
                error_msg = f"[UPLOADER][ERR] Failed to load Excel file: {e}"
                self.log_uploader(_ts() + error_msg)
                messagebox.showerror("File Error", f"Failed to load the Excel file:\n{e}")
                return
            
            # Check if this is an extractor log file (has "Client Name" column)
            is_extractor_log = "Client Name" in df.columns
            
            if is_extractor_log:
                # This is an extractor log - parse Client Name column
                self.log_uploader(_ts() + "[UPLOADER] Detected extractor log format - parsing Client Name column")
                self.log_uploader(_ts() + "[UPLOADER] Will use Date column from extractor log (PDF creation date)")
                first_names = []
                last_names = []
                dobs = []
                dates = []  # Store dates from extractor log (PDF creation dates)
                
                for idx, row in df.iterrows():
                    client_name = str(row.get("Client Name", "")).strip()
                    # Remove language prefix (e.g., "English ", "Spanish ")
                    if client_name.startswith("English "):
                        client_name = client_name.replace("English ", "", 1).strip()
                    elif client_name.startswith("Spanish "):
                        client_name = client_name.replace("Spanish ", "", 1).strip()
                    
                    # Parse name into first and last
                    name_parts = client_name.split(None, 1)  # Split on first space
                    if len(name_parts) >= 2:
                        first_name = name_parts[0].strip()
                        last_name = name_parts[1].strip()
                    else:
                        first_name = client_name
                        last_name = ""
                    
                    first_names.append(first_name)
                    last_names.append(last_name)
                    
                    # Get DOB from extractor log if available
                    dob_val = str(row.get("DOB", "")).strip()
                    if dob_val and dob_val.lower() not in ["nan", "none", ""]:
                        dobs.append(dob_val)
                    else:
                        dobs.append("")  # No DOB available
                    
                    # Get date from extractor log if available (this is the date from the PDF creation)
                    date_val = str(row.get("Date", "")).strip()
                    if date_val and date_val.lower() not in ["nan", "none", ""]:
                        dates.append(date_val)
                    else:
                        dates.append("")  # No date available
            else:
                # This is the original Excel file - use column mapping from uploader tab
                # Helper to convert column letter to index
                def col_letter_to_index(letter):
                    return ord(letter.upper()) - ord('A')
                
                # Check if Full Name column is provided
                col_full = self.uploader_col_full_name.get() if hasattr(self, 'uploader_col_full_name') else ""
                
                if col_full and col_full.strip():
                    # Use Full Name column - parse into first and last names
                    col_full_idx = col_letter_to_index(col_full.strip())
                    col_dob_letter = self.uploader_col_dob.get() if hasattr(self, 'uploader_col_dob') else self.col_dob.get()
                    col_dob_idx = col_letter_to_index(col_dob_letter)
                    
                    full_names_raw = df.iloc[:, col_full_idx].astype(str).tolist() if col_full_idx < len(df.columns) else [""] * len(df)
                    dobs_raw = df.iloc[:, col_dob_idx].astype(str).tolist() if col_dob_idx < len(df.columns) else [""] * len(df)
                    
                    # Parse full names into first and last names
                    first_names = []
                    last_names = []
                    for full_name in full_names_raw:
                        full_name_clean = re.sub(r'\s+', ' ', str(full_name).strip())
                        if full_name_clean and full_name_clean.lower() not in ["nan", "none", ""]:
                            # Split on first space
                            name_parts = full_name_clean.split(None, 1)
                            if len(name_parts) >= 2:
                                first_names.append(name_parts[0].strip())
                                last_names.append(name_parts[1].strip())
                            else:
                                first_names.append(full_name_clean)
                                last_names.append("")
                        else:
                            first_names.append("")
                            last_names.append("")
                    
                    dobs = [str(dob).strip() for dob in dobs_raw]
                else:
                    # Use separate First Name and Last Name columns
                    col_last = self.uploader_col_last_name.get() if hasattr(self, 'uploader_col_last_name') else self.col_last_name.get()
                    col_first = self.uploader_col_first_name.get() if hasattr(self, 'uploader_col_first_name') else self.col_first_name.get()
                    col_dob_letter = self.uploader_col_dob.get() if hasattr(self, 'uploader_col_dob') else self.col_dob.get()
                    
                    col_last_idx = col_letter_to_index(col_last)
                    col_first_idx = col_letter_to_index(col_first)
                    col_dob_idx = col_letter_to_index(col_dob_letter)
                    
                    # Get data from specified columns
                    # Clean up names: strip whitespace and normalize multiple spaces to single space
                    last_names_raw = df.iloc[:, col_last_idx].astype(str).tolist() if col_last_idx < len(df.columns) else [""] * len(df)
                    first_names_raw = df.iloc[:, col_first_idx].astype(str).tolist() if col_first_idx < len(df.columns) else [""] * len(df)
                    dobs_raw = df.iloc[:, col_dob_idx].astype(str).tolist() if col_dob_idx < len(df.columns) else [""] * len(df)
                    
                    # Clean names: strip and normalize spaces (re is imported at top of file)
                    last_names = [re.sub(r'\s+', ' ', str(name).strip()) for name in last_names_raw]
                    first_names = [re.sub(r'\s+', ' ', str(name).strip()) for name in first_names_raw]
                    dobs = [str(dob).strip() for dob in dobs_raw]
                
                # Get dates from Date column if available (NOT DOB - this is the date entered into the PDF)
                dates = []
                if "Date" in df.columns:
                    for date_val in df["Date"]:
                        if pd.notna(date_val):
                            # Convert datetime to string format
                            if isinstance(date_val, pd.Timestamp):
                                dates.append(date_val.strftime("%m/%d/%Y"))
                            else:
                                dates.append(str(date_val).strip())
                        else:
                            dates.append("")
                else:
                    # No Date column - dates will be empty, will fall back to PDF extraction or today's date
                    dates = [""] * len(df)
            
            self.log_uploader(_ts() + f"[UPLOADER] Found {len(last_names)} clients to upload")
            
            # Get the PDF folder where PDFs are located
            output_dir = self.uploader_pdf_folder.get()
            
            # Initialize Selenium
            webdriver, _By, _WebDriverWait, _EC, _Keys, Service, ChromeDriverManager = _lazy_import_selenium()
            
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            
            service = None
            try:
                service = Service(ChromeDriverManager().install())
            except:
                service = Service()
            
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 20)
            
            # Login to TherapyNotes ISWS
            self.log_uploader(_ts() + "[UPLOADER] Logging into TherapyNotes ISWS...")
            driver.get("https://www.therapynotes.com/app/login/IntegritySWS/?r=%2fapp%2fpatients%2f")
            
            # Wait for page to load
            time.sleep(3)
            
            # Try multiple selectors for username field
            username_field = None
            username_selectors = [
                (By.ID, "Login__UsernameField"),  # Specific to TherapyNotes ISWS
                (By.NAME, "username"),
                (By.ID, "Username"),
                (By.XPATH, "//input[@type='text']"),
                (By.XPATH, "//input[@type='text' or @type='email']"),
                (By.CSS_SELECTOR, "input[type='text'], input[type='email']"),
            ]
            
            for by, sel in username_selectors:
                try:
                    username_field = wait.until(EC.element_to_be_clickable((by, sel)))
                    break
                except:
                    continue
            
            if not username_field:
                self.log_uploader(_ts() + "[UPLOADER][ERR] Could not find username field")
                raise Exception("Could not find username field")
            
            # Scroll into view and click to focus
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", username_field)
            time.sleep(0.3)
            username_field.click()
            time.sleep(0.2)
            
            # Clear and enter username
            username_field.clear()
            username_field.send_keys(self.tn_username.get())
            self.log_uploader(_ts() + "[UPLOADER] Entered username")
            
            time.sleep(0.3)
            
            # Find and fill password field
            password_field = None
            password_selectors = [
                (By.ID, "Login__Password"),  # Specific to TherapyNotes ISWS
                (By.NAME, "Password"),
                (By.XPATH, "//input[@type='password']"),
            ]
            
            for by, sel in password_selectors:
                try:
                    password_field = wait.until(EC.element_to_be_clickable((by, sel)))
                    break
                except:
                    continue
            
            if not password_field:
                self.log_uploader(_ts() + "[UPLOADER][ERR] Could not find password field")
                raise Exception("Could not find password field")
            
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", password_field)
            time.sleep(0.3)
            password_field.click()
            time.sleep(0.2)
            password_field.send_keys(self.tn_password.get())
            self.log_uploader(_ts() + "[UPLOADER] Entered password")
            
            # Find and click login button - wait for it to be enabled
            login_selectors = [
                (By.ID, "Login__LogInButton"),  # Specific to TherapyNotes ISWS
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//button[@id='Login__LogInButton']"),
                (By.XPATH, "//button[contains(text(), 'Log In')]"),
                (By.XPATH, "//input[@type='submit']"),
            ]
            
            login_btn = None
            for by, sel in login_selectors:
                try:
                    # Wait for button to be enabled (aria-disabled becomes false)
                    login_btn = WebDriverWait(driver, 10).until(
                        lambda d: d.find_element(by, sel) if d.find_element(by, sel).get_attribute("aria-disabled") == "false" else None
                    )
                    break
                except:
                    # If that fails, just try to find it normally
                    try:
                        login_btn = driver.find_element(by, sel)
                        if login_btn.is_displayed() and login_btn.get_attribute("aria-disabled") != "true":
                            break
                    except:
                        continue
            
            if not login_btn:
                self.log_uploader(_ts() + "[UPLOADER][ERR] Could not find enabled login button")
                raise Exception("Could not find enabled login button")
            
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", login_btn)
            time.sleep(0.3)
            login_btn.click()
            self.log_uploader(_ts() + "[UPLOADER] Clicked login button")
            
            # Wait for login to complete
            time.sleep(4)
            
            # Navigate to Patients page
            def safe_return_to_patients(refresh_first=False):
                """Return to Patients list reliably, optionally refreshing the page first"""
                try:
                    # If refresh is requested, refresh the page first
                    if refresh_first:
                        self.log_uploader(_ts() + "[UPLOADER][RECOVERY] Refreshing page to recover from stuck state...")
                        driver.refresh()
                        time.sleep(3)  # Wait for page to reload
                    
                    # Try to find Patients link/button by text or SVG
                    patients_selectors = [
                        (By.LINK_TEXT, "Patients"),
                        (By.XPATH, "//a[contains(text(), 'Patients')]"),
                        (By.XPATH, "//button[contains(text(), 'Patients')]"),
                        (By.XPATH, "//a[.//svg[@id='circle-user-v6']]"),  # SVG icon
                        (By.XPATH, "//a[contains(@href, '/patients')]"),
                        (By.XPATH, "//*[contains(@class, 'nav')]//a[contains(text(), 'Patients')]"),
                    ]
                    
                    for by, sel in patients_selectors:
                        try:
                            link = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, sel)))
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
                            try:
                                link.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", link)
                            
                            # Wait for search box to appear
                            wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
                            time.sleep(0.4)
                            if refresh_first:
                                self.log_uploader(_ts() + "[UPLOADER][RECOVERY] Successfully recovered - returned to Patients page")
                            return True
                        except:
                            continue
                    
                    # Fallback: navigate directly to URL
                    driver.get("https://www.therapynotes.com/app/patients/list")
                    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
                    time.sleep(0.4)
                    if refresh_first:
                        self.log_uploader(_ts() + "[UPLOADER][RECOVERY] Successfully recovered - navigated to Patients page")
                    return True
                except Exception as e:
                    self.log_uploader(_ts() + f"[UPLOADER][WARN] Could not return to Patients page: {e}")
                    return False
            
            self.log_uploader(_ts() + "[UPLOADER] Navigating to Patients page...")
            safe_return_to_patients()
            
            # Process each client
            uploaded = 0
            skipped = 0
            successful_uploads = []  # Track successful uploads
            skipped_clients = []  # Track skipped clients with reasons
            
            for i, (first_name, last_name, dob) in enumerate(zip(first_names, last_names, dobs)):
                # Get date for this client if available (from Date column, NOT DOB)
                client_date = dates[i] if i < len(dates) else ""
                if not self.is_running:
                    break
                
                full_name = f"{first_name} {last_name}".strip()
                self.log_uploader(_ts() + f"[UPLOADER] Processing: {full_name}")
                # Debug: Log what date we're using (should be from Date column, not DOB)
                if client_date:
                    self.log_uploader(_ts() + f"[UPLOADER][DEBUG] Date from Excel Date column: {client_date} (DOB is: {dob})")
                
                # Find the PDF - ONLY look for NON-IPS PDFs (ISWS uploader should skip IPS PDFs)
                # Handle possible variations in spacing, but exclude IPS-prefixed files
                # Normalize spaces in names (handle multiple spaces, trailing spaces, etc.)
                first_clean = re.sub(r'\s+', ' ', str(first_name).strip())
                last_clean = re.sub(r'\s+', ' ', str(last_name).strip())
                
                pdf_filename_options = [
                    sanitize_filename(f"{first_clean} {last_clean} Consent NPP.pdf"),
                    sanitize_filename(f"{first_name.strip()} {last_name.strip()} Consent NPP.pdf"),
                    sanitize_filename(f"{first_name.strip()} {last_name.strip()}Consent NPP.pdf"),
                    # Also try with original spacing in case PDFs were created with extra spaces
                    sanitize_filename(f"{first_name} {last_name} Consent NPP.pdf"),
                ]
                
                pdf_path = None
                for filename_option in pdf_filename_options:
                    candidate_path = os.path.join(output_dir, filename_option)
                    if os.path.exists(candidate_path):
                        # Double-check it's not an IPS PDF (shouldn't happen, but safety check)
                        if not filename_option.upper().startswith("IPS"):
                            pdf_path = candidate_path
                            break
                
                # Debug: Log what we're looking for if PDF not found
                if not pdf_path:
                    self.log_uploader(_ts() + f"[UPLOADER][DEBUG] Looking in: {output_dir}")
                    self.log_uploader(_ts() + f"[UPLOADER][DEBUG] Tried filenames: {pdf_filename_options[:2]}")
                    # List some actual PDFs in the directory for debugging
                    try:
                        actual_pdfs = [f for f in os.listdir(output_dir) if f.endswith('.pdf') and not f.upper().startswith('IPS')]
                        if actual_pdfs:
                            sample_pdfs = actual_pdfs[:3]
                            self.log_uploader(_ts() + f"[UPLOADER][DEBUG] Sample PDFs in folder: {sample_pdfs}")
                    except Exception as e:
                        self.log_uploader(_ts() + f"[UPLOADER][DEBUG] Could not list PDFs: {e}")
                
                # Only skip if NO non-IPS PDF exists AND an IPS PDF exists
                # If both exist, we upload the non-IPS one (ISWS uploader)
                if not pdf_path:
                    # Check if ONLY an IPS PDF exists (no non-IPS PDF)
                    ips_pdf_options = [
                        sanitize_filename(f"IPS {first_name} {last_name} Consent NPP.pdf"),
                        sanitize_filename(f"IPS {first_name.strip()} {last_name.strip()} Consent NPP.pdf"),
                    ]
                    ips_pdf_exists = False
                    for ips_option in ips_pdf_options:
                        ips_candidate = os.path.join(output_dir, ips_option)
                        if os.path.exists(ips_candidate):
                            ips_pdf_exists = True
                            break
                    
                    # Skip if ONLY IPS PDF exists (this client should use IPS uploader)
                    if ips_pdf_exists:
                        self.log_uploader(_ts() + f"[UPLOADER][SKIP] Skipping IPS client {full_name} - only IPS PDF found, use IPS Uploader tab")
                        skipped += 1
                        skipped_clients.append(f"{full_name} - IPS client (only IPS PDF found, use IPS Uploader)")
                        continue
                    else:
                        self.log_uploader(_ts() + f"[UPLOADER][WARN] PDF not found for {first_name} {last_name}")
                        skipped += 1
                        skipped_clients.append(f"{full_name} - PDF not found")
                        continue
                
                # Search for patient by name
                self.log_uploader(_ts() + f"[UPLOADER] Searching for: {full_name}")
                
                try:
                    # Try specific ID first, then placeholder
                    search_box_selectors = [
                        (By.ID, "ctl00_BodyContent_TextBoxSearchPatientName"),  # Specific ID
                        (By.NAME, "ctl00$BodyContent$TextBoxSearchPatientName"),  # Name attribute
                        (By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']"),
                        (By.XPATH, "//input[@name='ctl00$BodyContent$TextBoxSearchPatientName']"),
                    ]
                    
                    search_box = None
                    for by, sel in search_box_selectors:
                        try:
                            search_box = wait.until(EC.element_to_be_clickable((by, sel)))
                            break
                        except:
                            continue
                    
                    if not search_box:
                        self.log_uploader(_ts() + "[UPLOADER][WARN] Could not find search box - attempting recovery...")
                        # Try to recover by refreshing and returning to Patients
                        if safe_return_to_patients(refresh_first=True):
                            self.log_uploader(_ts() + "[UPLOADER][RECOVERY] Recovery successful, continuing with next client")
                            skipped += 1
                            skipped_clients.append(f"{full_name} - Could not find search box (recovered)")
                            continue
                        else:
                            self.log_uploader(_ts() + "[UPLOADER][WARN] Recovery failed, skipping client")
                            skipped += 1
                            skipped_clients.append(f"{full_name} - Could not find search box (recovery failed)")
                            continue
                    
                    search_box.clear()
                    search_box.send_keys(full_name)
                    time.sleep(2)  # Increased wait time
                    
                    # Wait for dropdown and find the result matching DOB
                    # The dropdown container is ContentBubbleResultsContainer
                    matched_patient = None
                    
                    try:
                        # Wait for the container to appear AND for results to be populated
                        results_container = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "ContentBubbleResultsContainer"))
                        )
                        self.log_uploader(_ts() + "[UPLOADER] Dropdown container appeared")
                        
                        # Wait a bit more for results to populate
                        time.sleep(0.5)
                        
                        # Try multiple selectors for the results
                        results = []
                        result_selectors = [
                            "div.ui-menu-item",
                            ".ui-menu-item",
                            "li.ui-menu-item",
                            "a.ui-menu-item",
                            "*[class*='menu-item']",
                            "div[class*='result']",
                        ]
                        
                        for sel in result_selectors:
                            # Search within the container, not globally
                            try:
                                results = results_container.find_elements(By.CSS_SELECTOR, sel)
                                if results:
                                    self.log_uploader(_ts() + f"[UPLOADER] Found {len(results)} results using selector: {sel}")
                                    break
                            except:
                                continue
                        
                        # Also try finding any clickable elements in the container
                        if not results:
                            all_elements = results_container.find_elements(By.TAG_NAME, "*")
                            clickable = [el for el in all_elements if el.is_displayed() and el.text.strip()]
                            if clickable:
                                results = clickable[:5]  # Limit to first 5
                                self.log_uploader(_ts() + f"[UPLOADER] Found {len(results)} clickable elements in container")
                        
                        self.log_uploader(_ts() + f"[UPLOADER] Total results found: {len(results)}")
                        
                        # Look for a result that contains the DOB
                        if dob and dob.strip() and str(dob).strip() != "nan":
                            # Log the DOB we're looking for
                            self.log_uploader(_ts() + f"[UPLOADER] Looking for DOB: {dob}")
                            
                            # Normalize DOB format for comparison (handle various formats)
                            dob_str = str(dob).strip()
                            dob_normalized = dob_str.replace('/', '').replace('-', '').replace(' ', '').strip()
                            
                            # Extract year digits (last 2 digits)
                            year_digits = None
                            try:
                                # Try to extract last 2 digits of year
                                parts = re.split(r'[/-]', dob_str)
                                if len(parts) >= 3:
                                    # Check if first part is 4 digits (YYYY-MM-DD format)
                                    if len(parts[0]) == 4:
                                        # ISO format: YYYY-MM-DD or YYYY/MM/DD
                                        year_part = parts[0]  # Year is first part
                                        if len(year_part) == 4:
                                            year_digits = year_part[-2:]  # Last 2 digits of year (e.g., "1960" -> "60")
                                    else:
                                        # American format: MM/DD/YYYY or MM-DD-YYYY
                                        year_part = parts[-1]  # Year is last part
                                        if len(year_part) >= 2:
                                            year_digits = year_part[-2:]
                            except:
                                pass
                            
                            self.log_uploader(_ts() + f"[UPLOADER] Normalized DOB: {dob_normalized}, Year: {year_digits}")
                            
                            for result in results:
                                result_text = result.text.strip()
                                # Log each result for debugging
                                self.log_uploader(_ts() + f"[UPLOADER] Checking result: {result_text[:100]}")
                                
                                result_normalized = result_text.replace('/', '').replace('-', '').replace(' ', '').replace(' ', '')
                                
                                # Check if full DOB matches
                                if dob_normalized in result_normalized:
                                    matched_patient = result
                                    self.log_uploader(_ts() + f"[UPLOADER] Matched by full DOB: {dob}")
                                    break
                                
                                # Check if year digits match
                                if year_digits and year_digits in result_text:
                                    matched_patient = result
                                    self.log_uploader(_ts() + f"[UPLOADER] Matched by year: {year_digits}")
                                    break
                        
                        # If no DOB match, just take the first result
                        if matched_patient is None and results:
                            matched_patient = results[0]
                            self.log_uploader(_ts() + "[UPLOADER] No DOB match, selecting first result")
                        
                        if matched_patient:
                            # Click patient - use JavaScript if regular click fails
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", matched_patient)
                                time.sleep(0.3)
                                matched_patient.click()
                            except:
                                # Fallback to JavaScript click
                                driver.execute_script("arguments[0].click();", matched_patient)
                            time.sleep(2)
                            
                            # Wait for any dialogs/modals to appear and close them if needed
                            try:
                                # Check for common dialog/modal close buttons
                                close_selectors = [
                                    (By.XPATH, "//button[contains(@class, 'close')]"),
                                    (By.XPATH, "//button[@aria-label='Close']"),
                                    (By.XPATH, "//button[contains(., '×')]"),
                                    (By.CSS_SELECTOR, ".Dialog button.close"),
                                ]
                                for by, sel in close_selectors:
                                    try:
                                        close_btn = driver.find_element(by, sel)
                                        if close_btn.is_displayed():
                                            driver.execute_script("arguments[0].click();", close_btn)
                                            time.sleep(0.5)
                                            break
                                    except:
                                        continue
                            except:
                                pass
                        else:
                            raise Exception("No results found in dropdown")
                            
                    except Exception as e:
                        self.log_uploader(_ts() + f"[UPLOADER][WARN] Could not select patient from dropdown: {e}")
                        skipped += 1
                        skipped_clients.append(f"{full_name} - Could not select from dropdown: {str(e)[:50]}")
                        # Try to recover by refreshing and returning to Patients
                        self.log_uploader(_ts() + "[UPLOADER][RECOVERY] Attempting recovery after dropdown selection failure...")
                        safe_return_to_patients(refresh_first=True)
                        continue
                        
                except Exception as e:
                    self.log_uploader(_ts() + f"[UPLOADER][WARN] Could not search/find patient: {e}")
                    skipped += 1
                    skipped_clients.append(f"{full_name} - Search failed: {str(e)[:50]}")
                    # Try to recover by refreshing and returning to Patients
                    self.log_uploader(_ts() + "[UPLOADER][RECOVERY] Attempting recovery after search failure...")
                    safe_return_to_patients(refresh_first=True)
                    continue
                
                # Open Documents tab
                try:
                    docs_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-tab-id='Documents']")))
                    # Try regular click first, fallback to JavaScript
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", docs_tab)
                        time.sleep(0.3)
                        docs_tab.click()
                    except:
                        driver.execute_script("arguments[0].click();", docs_tab)
                    time.sleep(1.5)  # Increased wait time for Documents tab to load
                except Exception as e:
                    self.log_uploader(_ts() + f"[UPLOADER][WARN] Could not open Documents tab: {e}")
                    skipped += 1
                    skipped_clients.append(f"{full_name} - Could not open Documents tab: {str(e)[:50]}")
                    # Try to recover by refreshing and returning to Patients
                    self.log_uploader(_ts() + "[UPLOADER][RECOVERY] Attempting recovery after Documents tab failure...")
                    safe_return_to_patients(refresh_first=True)
                    continue
                
                # Wait for any dialogs to close before trying to open upload dialog
                time.sleep(1)
                
                # Try to close any blocking dialogs
                try:
                    dialog_selectors = [
                        (By.CSS_SELECTOR, ".Dialog"),
                        (By.CSS_SELECTOR, "[class*='Dialog']"),
                        (By.CSS_SELECTOR, "[class*='modal']"),
                    ]
                    for by, sel in dialog_selectors:
                        try:
                            dialogs = driver.find_elements(by, sel)
                            for dialog in dialogs:
                                if dialog.is_displayed():
                                    # Try to find and click close button in dialog
                                    close_btns = dialog.find_elements(By.XPATH, ".//button[contains(@class, 'close') or contains(., '×') or @aria-label='Close']")
                                    for close_btn in close_btns:
                                        if close_btn.is_displayed():
                                            driver.execute_script("arguments[0].click();", close_btn)
                                            time.sleep(0.5)
                                            break
                        except:
                            continue
                except:
                    pass
                
                # Open upload dialog
                try:
                    # Wait for upload button with multiple selectors
                    upload_btn = None
                    upload_selectors = [
                        (By.XPATH, "//button[contains(., 'Upload Patient File')]"),
                        (By.XPATH, "//button[contains(text(), 'Upload')]"),
                        (By.XPATH, "//button[contains(@class, 'upload')]"),
                        (By.ID, "btnUploadPatientFile"),
                    ]
                    
                    for by, sel in upload_selectors:
                        try:
                            upload_btn = wait.until(EC.presence_of_element_located((by, sel)))
                            if upload_btn.is_displayed():
                                break
                        except:
                            continue
                    
                    if not upload_btn:
                        raise Exception("Upload button not found")
                    
                    # Try to click with JavaScript to avoid interception
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", upload_btn)
                        time.sleep(0.3)
                        # Try regular click first
                        upload_btn.click()
                    except:
                        # Fallback to JavaScript click
                        driver.execute_script("arguments[0].click();", upload_btn)
                    time.sleep(1)  # Increased wait time for dialog to open
                except Exception as e:
                    self.log_uploader(_ts() + f"[UPLOADER][WARN] Could not open upload dialog: {e}")
                    skipped += 1
                    skipped_clients.append(f"{full_name} - Could not open upload dialog: {str(e)[:50]}")
                    # Try to recover by refreshing and returning to Patients
                    self.log_uploader(_ts() + "[UPLOADER][RECOVERY] Attempting recovery after upload dialog failure...")
                    safe_return_to_patients(refresh_first=True)
                    continue
                
                # Fill upload form
                try:
                    # Date field - use date from Excel Date column (NOT DOB), then try PDF extraction, then today's date
                    date_field = wait.until(EC.element_to_be_clickable((By.ID, "PatientFile__Date")))
                    date_field.clear()
                    
                    # IMPORTANT: Use date from Excel Date column (NOT DOB - DOB is only for patient matching)
                    # client_date should be from the Date column (or extractor log Date column which contains PDF creation date)
                    if client_date and client_date.strip() and client_date.lower() not in ["nan", "none", ""]:
                        # Date from Excel Date column or extractor log - format it properly
                        try:
                            # Try to parse and format the date
                            date_obj = None
                            # Try common date formats
                            date_formats = ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%y", "%m-%d-%y"]
                            for fmt in date_formats:
                                try:
                                    date_obj = DT.strptime(client_date.strip(), fmt)
                                    # Validate the date is reasonable (not malformed like "11/4/125")
                                    if date_obj.year < 1900 or date_obj.year > 2100:
                                        date_obj = None
                                        continue
                                    # Additional check: if the date matches the DOB exactly, it's probably wrong
                                    # (DOB should not be used as document date - document dates are usually recent)
                                    # However, if using extractor log, the Date column is the PDF creation date, not DOB
                                    if dob and dob.strip():
                                        try:
                                            dob_str = str(dob).strip()
                                            # Try to parse DOB and compare
                                            for dob_fmt in date_formats:
                                                try:
                                                    dob_obj = DT.strptime(dob_str, dob_fmt)
                                                    if date_obj == dob_obj:
                                                        # Date matches DOB - this is suspicious
                                                        # But if it's from extractor log, it might be legitimate if DOB was used as date
                                                        # Check if date is recent (likely document date) vs old (likely DOB)
                                                        if date_obj.year < 2000:
                                                            # Old date matching DOB - definitely wrong
                                                            self.log_uploader(_ts() + f"[UPLOADER][WARN] Date matches DOB and is old ({date_obj.year}) - likely wrong! Date: {client_date}, DOB: {dob}")
                                                            self.log_uploader(_ts() + f"[UPLOADER][WARN] Skipping Date column value (matches DOB), will try PDF extraction instead")
                                                            date_obj = None
                                                            break
                                                        else:
                                                            # Recent date matching DOB - might be legitimate (e.g., someone born in 2000s)
                                                            self.log_uploader(_ts() + f"[UPLOADER][INFO] Date matches DOB but is recent ({date_obj.year}) - using it as document date")
                                                except:
                                                    continue
                                            if date_obj is None:
                                                break
                                        except:
                                            pass
                                    break
                                except:
                                    continue
                            
                            if date_obj:
                                date_str = date_obj.strftime("%m/%d/%Y")
                                if is_extractor_log:
                                    self.log_uploader(_ts() + f"[UPLOADER] Using date from extractor log (PDF creation date): {date_str}")
                                else:
                                    self.log_uploader(_ts() + f"[UPLOADER] Using date from Excel Date column: {date_str}")
                            else:
                                # If parsing fails or date is invalid/matches DOB, try PDF extraction
                                self.log_uploader(_ts() + f"[UPLOADER][WARN] Date from Excel column invalid or matches old DOB, trying PDF extraction...")
                                extracted_date = None
                                try:
                                    extracted_date = self._extract_date_from_pdf(pdf_path)
                                except:
                                    pass
                                if extracted_date:
                                    date_str = extracted_date
                                    self.log_uploader(_ts() + f"[UPLOADER] Using date extracted from PDF: {date_str}")
                                else:
                                    date_str = DT.now().strftime("%m/%d/%Y")
                                    self.log_uploader(_ts() + f"[UPLOADER][WARN] No valid date found, using today: {date_str}")
                        except Exception as e:
                            self.log_uploader(_ts() + f"[UPLOADER][WARN] Could not parse date '{client_date}': {e}, trying PDF extraction...")
                            extracted_date = None
                            try:
                                extracted_date = self._extract_date_from_pdf(pdf_path)
                            except:
                                pass
                            if extracted_date:
                                date_str = extracted_date
                                self.log_uploader(_ts() + f"[UPLOADER] Using date extracted from PDF: {date_str}")
                            else:
                                date_str = DT.now().strftime("%m/%d/%Y")
                                self.log_uploader(_ts() + f"[UPLOADER] Using today's date: {date_str}")
                    else:
                        # No date available from Excel Date column, try to extract from PDF
                        try:
                            extracted_date = self._extract_date_from_pdf(pdf_path)
                            if extracted_date:
                                date_str = extracted_date
                                self.log_uploader(_ts() + f"[UPLOADER] Using date extracted from PDF: {date_str}")
                            else:
                                date_str = DT.now().strftime("%m/%d/%Y")
                                self.log_uploader(_ts() + f"[UPLOADER] No date found, using today's date: {date_str}")
                        except Exception as e:
                            self.log_uploader(_ts() + f"[UPLOADER][WARN] Could not extract date from PDF: {e}, using today's date")
                            date_str = DT.now().strftime("%m/%d/%Y")
                    
                    date_field.send_keys(date_str)
                    time.sleep(0.2)
                    
                    # File input
                    file_input = wait.until(EC.presence_of_element_located((By.ID, "InputUploader")))
                    file_input.send_keys(os.path.abspath(pdf_path))
                    time.sleep(0.6)
                    
                    # Document name
                    doc_name = wait.until(EC.element_to_be_clickable((By.ID, "PatientFile__DocumentName")))
                    doc_name.clear()
                    doc_name.send_keys(f"{first_name} {last_name} Consent NPP")
                    time.sleep(0.2)
                    
                    # Click away on a blank part of the upload dialog to activate the button
                    self.log_uploader(_ts() + "[UPLOADER] Clicking away to activate Add Document button...")
                    try:
                        # Try to click on the dialog background or a label
                        # Click on a label element or the dialog container itself
                        dialog_or_label = driver.find_element(By.XPATH, "//label[text()='Patient']")
                        dialog_or_label.click()
                        time.sleep(0.3)
                    except:
                        try:
                            # Try clicking on the dialog container
                            dialog_container = driver.find_element(By.CLASS_NAME, "modal-body")
                            dialog_container.click()
                            time.sleep(0.3)
                        except:
                            # Just send Tab to move focus away
                            from selenium.webdriver.common.keys import Keys
                            doc_name.send_keys(Keys.TAB)
                            time.sleep(0.3)
                    
                    # Click Add Document
                    add_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='button' and @value='Add Document']")))
                    add_btn.click()
                    time.sleep(2)
                    
                    self.log_uploader(_ts() + f"[UPLOADER] ✓ Uploaded: {full_name}")
                    uploaded += 1
                    successful_uploads.append(full_name)
                except Exception as e:
                    self.log_uploader(_ts() + f"[UPLOADER][WARN] Upload failed: {e}")
                    skipped += 1
                    skipped_clients.append(f"{full_name} - Upload failed: {str(e)[:50]}")
                    # Try to recover by refreshing and returning to Patients
                    self.log_uploader(_ts() + "[UPLOADER][RECOVERY] Attempting recovery after upload failure...")
                    safe_return_to_patients(refresh_first=True)
                    continue
                
                # Return to Patients page for next client
                if i < len(first_names) - 1:  # Don't return on last client
                    self.log_uploader(_ts() + f"[UPLOADER] Returning to Patients page...")
                    safe_return_to_patients()
            
            self.log_uploader(_ts() + f"[UPLOADER] Complete! Uploaded: {uploaded}, Skipped: {skipped}")
            
            # Generate report
            self._generate_upload_report(successful_uploads, skipped_clients, uploaded, skipped)
            
            self.uploader_start_btn.config(state="normal")
            self.uploader_stop_btn.config(state="disabled")
            self.is_running = False
            
        except Exception as e:
            self.log_uploader(_ts() + f"[UPLOADER][ERR] {e}")
            import traceback
            self.log_uploader(traceback.format_exc())
            self.uploader_start_btn.config(state="normal")
            self.uploader_stop_btn.config(state="disabled")
            self.is_running = False
    
    def _generate_upload_report(self, successful_uploads, skipped_clients, uploaded, skipped):
        """Generate and save upload report to user's desktop and Excel log to selected location"""
        try:
            # Generate text report (keep existing functionality)
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            timestamp = DT.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(desktop_path, f"Consent_Upload_Report_{timestamp}.txt")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("CONSENT FORM UPLOAD REPORT\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Report generated: {DT.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write(f"SUMMARY\n")
                f.write("-" * 50 + "\n")
                f.write(f"Total Clients Processed: {uploaded + skipped}\n")
                f.write(f"Successfully Uploaded: {uploaded}\n")
                f.write(f"Skipped: {skipped}\n\n")
                
                if successful_uploads:
                    f.write("SUCCESSFULLY UPLOADED CLIENTS\n")
                    f.write("-" * 50 + "\n")
                    for i, client in enumerate(successful_uploads, 1):
                        f.write(f"{i}. {client}\n")
                    f.write("\n")
                
                if skipped_clients:
                    f.write("SKIPPED CLIENTS\n")
                    f.write("-" * 50 + "\n")
                    for i, client in enumerate(skipped_clients, 1):
                        f.write(f"{i}. {client}\n")
                    f.write("\n")
                
                f.write("=" * 50 + "\n")
                f.write("Report complete.\n")
            
            self.log_uploader(_ts() + f"[REPORT] Upload report saved to: {report_path}")
            
            # Generate Excel log
            output_dir = self.uploader_output_dir.get()
            if not output_dir:
                output_dir = desktop_path
            os.makedirs(output_dir, exist_ok=True)
            
            # Prepare Excel log rows
            log_rows = []
            for client in successful_uploads:
                log_rows.append({
                    'Client Name': client,
                    'Status': 'Uploaded',
                    'Reason': 'Success'
                })
            for client_reason in skipped_clients:
                # Parse client name and reason from "Client Name - Reason" format
                if ' - ' in client_reason:
                    client_name, reason = client_reason.split(' - ', 1)
                else:
                    client_name = client_reason
                    reason = 'Unknown'
                log_rows.append({
                    'Client Name': client_name,
                    'Status': 'Skipped',
                    'Reason': reason
                })
            
            # Add summary row
            log_rows.append({
                'Client Name': '=== SUMMARY ===',
                'Status': f'Total: {uploaded + skipped}',
                'Reason': f'Uploaded: {uploaded}, Skipped: {skipped}'
            })
            
            # Save Excel log
            log_filename = f"Consent_Uploader_Log_{timestamp}.xlsx"
            log_path = os.path.join(output_dir, log_filename)
            df = pd.DataFrame(log_rows)
            df.to_excel(log_path, index=False)
            self.log_uploader(_ts() + f"[REPORT] Excel log saved to: {log_path}")
            
            messagebox.showinfo("Report Generated", f"Upload report saved to:\n{report_path}\n\nExcel log saved to:\n{log_path}")
        
        except Exception as e:
            self.log_uploader(_ts() + f"[REPORT][WARN] Could not generate report: {e}")
    
    def log_uploader(self, message):
        """Log messages to the uploader log area"""
        self.uploader_log_text.insert(tk.END, message + "\n")
        self.uploader_log_text.see(tk.END)
        self.root.update_idletasks()
    
    def _build_ips_uploader_tab(self):
        """Build the IPS Uploader tab - similar to ISWS Uploader but for IPS clients"""
        # Create scrollable frame for IPS uploader
        scrollable_frame = self._create_scrollable_frame(self.ips_uploader_tab)
        
        # Main container for IPS uploader
        main_frame = tk.Frame(scrollable_frame)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        main_frame.configure(width=600)
        
        # TherapyNotes Credentials section
        cred_frame = tk.LabelFrame(main_frame, text="TherapyNotes IPS Credentials", font=("Arial", 10, "bold"))
        cred_frame.pack(fill="x", pady=3)
        cred_frame.columnconfigure(1, weight=1)
        
        # User Selection Row
        tk.Label(cred_frame, text="Saved User:", font=("Arial", 10)).grid(row=0, column=0, sticky="e", padx=5, pady=5)
        
        # User Selection Dropdown
        self.ips_therapynotes_user_dropdown = ttk.Combobox(cred_frame, font=("Arial", 9), width=25, state="readonly")
        self.ips_therapynotes_user_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.ips_therapynotes_user_dropdown.bind("<<ComboboxSelected>>", self._on_ips_therapynotes_user_selected)
        self._update_ips_therapynotes_user_dropdown()
        
        # Add User button
        tk.Button(cred_frame, text="Add User", command=self._add_ips_therapynotes_user,
                 bg=MAROON, fg="white", font=("Arial", 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=0, column=2, padx=5, pady=5)
        
        # Update User button
        tk.Button(cred_frame, text="Update User", command=self._update_ips_therapynotes_user,
                 bg="#666666", fg="white", font=("Arial", 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=0, column=3, padx=5, pady=5)
        
        # Credentials fields
        tk.Label(cred_frame, text="Username:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(cred_frame, textvariable=self.ips_tn_username).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        tk.Label(cred_frame, text="Password:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(cred_frame, textvariable=self.ips_tn_password, show="*").grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        # File Selection section
        files_frame = tk.LabelFrame(main_frame, text="File Selection", font=("Arial", 10, "bold"))
        files_frame.pack(fill="x", pady=3)
        files_frame.columnconfigure(2, weight=1)
        
        tk.Label(files_frame, text="Excel/CSV:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        tk.Button(files_frame, text="Select File", command=self._pick_ips_uploader_excel).grid(row=0, column=1, padx=5, pady=5)
        self.ips_uploader_excel_label = tk.Label(files_frame, text="No file selected")
        self.ips_uploader_excel_label.grid(row=0, column=2, sticky="w", padx=5, pady=5)
        
        tk.Label(files_frame, text="PDF Folder:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        tk.Button(files_frame, text="Select Folder", command=self._pick_ips_uploader_folder).grid(row=1, column=1, padx=5, pady=5)
        self.ips_uploader_folder_label = tk.Label(files_frame, text="No folder selected")
        self.ips_uploader_folder_label.grid(row=1, column=2, sticky="w", padx=5, pady=5)
        
        # Output location section
        output_frame = tk.LabelFrame(main_frame, text="Output Location (Excel Logs)", font=("Arial", 10, "bold"))
        output_frame.pack(fill="x", pady=3)
        output_frame.columnconfigure(1, weight=1)
        
        tk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(output_frame, textvariable=self.ips_uploader_output_dir, width=50).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        tk.Button(output_frame, text="Browse", command=self._pick_ips_uploader_output_dir).grid(row=0, column=2, padx=5, pady=5)
        
        # Column mapping section (for non-extractor log files)
        mapping_frame = tk.LabelFrame(main_frame, text="Column Mapping (for non-extractor log files)", font=("Arial", 10, "bold"))
        mapping_frame.pack(fill="x", pady=3)
        
        # Row 1: Full Name (if provided, will be used instead of separate First/Last)
        tk.Label(mapping_frame, text="Full Name:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.ips_uploader_col_full_name = tk.StringVar(value="")
        tk.Entry(mapping_frame, textvariable=self.ips_uploader_col_full_name, width=5).grid(row=0, column=1, padx=5, pady=2)
        tk.Label(mapping_frame, text="(optional - if filled, First/Last Name columns ignored)", font=("Arial", 8), fg="gray").grid(row=0, column=2, columnspan=4, sticky="w", padx=5, pady=2)
        
        # Row 2: Name and DOB columns
        tk.Label(mapping_frame, text="Last Name:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.ips_uploader_col_last_name = tk.StringVar(value=self.col_last_name.get())
        tk.Entry(mapping_frame, textvariable=self.ips_uploader_col_last_name, width=5).grid(row=1, column=1, padx=5, pady=2)
        
        tk.Label(mapping_frame, text="First Name:").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        self.ips_uploader_col_first_name = tk.StringVar(value=self.col_first_name.get())
        tk.Entry(mapping_frame, textvariable=self.ips_uploader_col_first_name, width=5).grid(row=1, column=3, padx=5, pady=2)
        
        tk.Label(mapping_frame, text="DOB:").grid(row=1, column=4, sticky="e", padx=5, pady=2)
        self.ips_uploader_col_dob = tk.StringVar(value=self.col_dob.get())
        tk.Entry(mapping_frame, textvariable=self.ips_uploader_col_dob, width=5).grid(row=1, column=5, padx=5, pady=2)
        
        # Row 3: Date and Counselor columns
        tk.Label(mapping_frame, text="Date:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.ips_uploader_col_date = tk.StringVar(value="D")  # Default to column D
        tk.Entry(mapping_frame, textvariable=self.ips_uploader_col_date, width=5).grid(row=2, column=1, padx=5, pady=2)
        
        tk.Label(mapping_frame, text="Counselor:").grid(row=2, column=2, sticky="e", padx=5, pady=2)
        self.ips_uploader_col_counselor = tk.StringVar(value=self.col_counselor.get())
        tk.Entry(mapping_frame, textvariable=self.ips_uploader_col_counselor, width=5).grid(row=2, column=3, padx=5, pady=2)
        
        info_text = "This uploader will only upload PDFs with the 'IPS' prefix (e.g., 'IPS First Last Consent NPP.pdf').\nNote: If the file is an extractor log (has 'Client Name' column), column mapping is ignored."
        tk.Label(mapping_frame, text=info_text, justify="left", wraplength=600, font=("Arial", 8)).grid(row=3, column=0, columnspan=6, sticky="w", padx=5, pady=2)
        
        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=5)
        
        self.ips_uploader_start_btn = tk.Button(btn_frame, text="Start Upload", command=self._start_ips_uploader, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
        self.ips_uploader_start_btn.pack(side="left", padx=5)
        
        self.ips_uploader_stop_btn = tk.Button(btn_frame, text="Stop", command=self._stop_bot, state="disabled", bg="#f44336", fg="white", font=("Arial", 12))
        self.ips_uploader_stop_btn.pack(side="left", padx=5)
        
        # Log area
        log_frame = tk.LabelFrame(main_frame, text="IPS Uploader Log", font=("Arial", 10, "bold"))
        log_frame.pack(fill="both", expand=True, pady=3)
        
        self.ips_uploader_log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Courier", 9))
        self.ips_uploader_log_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def _pick_ips_uploader_excel(self):
        f = filedialog.askopenfilename(filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"), ("All files", "*.*")])
        if f:
            self.ips_uploader_excel_path.set(f)
            self.ips_uploader_excel_label.config(text=os.path.basename(f))
    
    def _pick_ips_uploader_folder(self):
        f = filedialog.askdirectory()
        if f:
            self.ips_uploader_pdf_folder.set(f)
            self.ips_uploader_folder_label.config(text=os.path.basename(f))
    
    def _pick_ips_uploader_output_dir(self):
        d = filedialog.askdirectory(initialdir=self.ips_uploader_output_dir.get())
        if d:
            self.ips_uploader_output_dir.set(d)
    
    def _start_ips_uploader(self):
        """Start the IPS uploader bot"""
        if not self.ips_uploader_excel_path.get():
            messagebox.showerror("Error", "Please select the Excel/CSV file in the IPS Uploader tab")
            return
        if not self.ips_uploader_pdf_folder.get():
            messagebox.showerror("Error", "Please select the PDF folder in the IPS Uploader tab")
            return
        if not self.ips_tn_username.get() or not self.ips_tn_password.get():
            messagebox.showerror("Error", "Please enter TherapyNotes IPS credentials")
            return
        
        self.ips_uploader_start_btn.config(state="disabled")
        self.ips_uploader_stop_btn.config(state="normal")
        self.is_running = True
        self.stop_flag.clear()
        
        # Start IPS uploader in thread
        thread = threading.Thread(target=self._run_ips_uploader, daemon=True)
        thread.start()
    
    def _run_ips_uploader(self):
        """Run the IPS uploader bot to upload IPS-prefixed PDFs to TherapyNotes IPS"""
        # This is a simplified version - reuses most of the ISWS uploader logic
        # but only looks for IPS-prefixed PDFs and uses IPS login URL
        try:
            import pandas as pd
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException
            
            # Load Excel (same logic as ISWS uploader)
            try:
                df = pd.read_excel(self.ips_uploader_excel_path.get())
            except PermissionError as e:
                self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][ERR] Permission denied: Cannot read the Excel file.")
                messagebox.showerror("Permission Error", "Cannot read the Excel file. Please close it and try again.")
                return
            except Exception as e:
                self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][ERR] Failed to load Excel file: {e}")
                messagebox.showerror("File Error", f"Failed to load the Excel file:\n{e}")
                return
            
            # Parse Excel (same logic as ISWS uploader)
            is_extractor_log = "Client Name" in df.columns
            
            if is_extractor_log:
                self.log_ips_uploader(_ts() + "[IPS-UPLOADER] Detected extractor log format - parsing Client Name column")
                self.log_ips_uploader(_ts() + "[IPS-UPLOADER] Will use Date column from extractor log (PDF creation date)")
                first_names = []
                last_names = []
                dobs = []
                dates = []
                
                for idx, row in df.iterrows():
                    client_name = str(row.get("Client Name", "")).strip()
                    if client_name.startswith("English "):
                        client_name = client_name.replace("English ", "", 1).strip()
                    elif client_name.startswith("Spanish "):
                        client_name = client_name.replace("Spanish ", "", 1).strip()
                    
                    # Normalize spaces in client name
                    client_name = re.sub(r'\s+', ' ', client_name)
                    
                    name_parts = client_name.split(None, 1)
                    if len(name_parts) >= 2:
                        first_names.append(name_parts[0].strip())
                        last_names.append(name_parts[1].strip())
                    else:
                        first_names.append(client_name)
                        last_names.append("")
                    
                    dob_val = str(row.get("DOB", "")).strip()
                    dobs.append(dob_val if dob_val and dob_val.lower() not in ["nan", "none", ""] else "")
                    
                    date_val = str(row.get("Date", "")).strip()
                    dates.append(date_val if date_val and date_val.lower() not in ["nan", "none", ""] else "")
            else:
                def col_letter_to_index(letter):
                    return ord(letter.upper()) - ord('A')
                
                # Check if Full Name column is provided
                col_full = self.ips_uploader_col_full_name.get() if hasattr(self, 'ips_uploader_col_full_name') else ""
                
                if col_full and col_full.strip():
                    # Use Full Name column - parse into first and last names
                    col_full_idx = col_letter_to_index(col_full.strip())
                    col_dob_letter = self.ips_uploader_col_dob.get() if hasattr(self, 'ips_uploader_col_dob') else self.col_dob.get()
                    col_dob_idx = col_letter_to_index(col_dob_letter)
                    
                    full_names_raw = df.iloc[:, col_full_idx].astype(str).tolist() if col_full_idx < len(df.columns) else [""] * len(df)
                    dobs_raw = df.iloc[:, col_dob_idx].astype(str).tolist() if col_dob_idx < len(df.columns) else [""] * len(df)
                    
                    # Parse full names into first and last names
                    first_names = []
                    last_names = []
                    for full_name in full_names_raw:
                        full_name_clean = re.sub(r'\s+', ' ', str(full_name).strip())
                        if full_name_clean and full_name_clean.lower() not in ["nan", "none", ""]:
                            # Split on first space
                            name_parts = full_name_clean.split(None, 1)
                            if len(name_parts) >= 2:
                                first_names.append(name_parts[0].strip())
                                last_names.append(name_parts[1].strip())
                            else:
                                first_names.append(full_name_clean)
                                last_names.append("")
                        else:
                            first_names.append("")
                            last_names.append("")
                    
                    dobs = [str(dob).strip() for dob in dobs_raw]
                else:
                    # Use separate First Name and Last Name columns
                    col_last = self.ips_uploader_col_last_name.get() if hasattr(self, 'ips_uploader_col_last_name') else self.col_last_name.get()
                    col_first = self.ips_uploader_col_first_name.get() if hasattr(self, 'ips_uploader_col_first_name') else self.col_first_name.get()
                    col_dob_letter = self.ips_uploader_col_dob.get() if hasattr(self, 'ips_uploader_col_dob') else self.col_dob.get()
                    
                    col_last_idx = col_letter_to_index(col_last)
                    col_first_idx = col_letter_to_index(col_first)
                    col_dob_idx = col_letter_to_index(col_dob_letter)
                    
                    # Clean up names: strip whitespace and normalize multiple spaces to single space
                    last_names_raw = df.iloc[:, col_last_idx].astype(str).tolist() if col_last_idx < len(df.columns) else [""] * len(df)
                    first_names_raw = df.iloc[:, col_first_idx].astype(str).tolist() if col_first_idx < len(df.columns) else [""] * len(df)
                    dobs_raw = df.iloc[:, col_dob_idx].astype(str).tolist() if col_dob_idx < len(df.columns) else [""] * len(df)
                    
                    # Clean names: strip and normalize spaces (re is imported at top of file)
                    last_names = [re.sub(r'\s+', ' ', str(name).strip()) for name in last_names_raw]
                    first_names = [re.sub(r'\s+', ' ', str(name).strip()) for name in first_names_raw]
                    dobs = [str(dob).strip() for dob in dobs_raw]
                
                # Get dates from Date column if available (NOT DOB - this is the date entered into the PDF)
                dates = []
                # Try to get Date column by name first, then by column mapping
                if "Date" in df.columns:
                    for date_val in df["Date"]:
                        if pd.notna(date_val):
                            # Convert datetime to string format
                            if isinstance(date_val, pd.Timestamp):
                                dates.append(date_val.strftime("%m/%d/%Y"))
                            else:
                                dates.append(str(date_val).strip())
                        else:
                            dates.append("")
                elif hasattr(self, 'ips_uploader_col_date') and self.ips_uploader_col_date.get():
                    # Use column mapping for Date column
                    col_date_idx = col_letter_to_index(self.ips_uploader_col_date.get())
                    if col_date_idx < len(df.columns):
                        for date_val in df.iloc[:, col_date_idx]:
                            if pd.notna(date_val):
                                if isinstance(date_val, pd.Timestamp):
                                    dates.append(date_val.strftime("%m/%d/%Y"))
                                else:
                                    dates.append(str(date_val).strip())
                            else:
                                dates.append("")
                    else:
                        dates = [""] * len(df)
                else:
                    # No Date column - dates will be empty, will fall back to PDF extraction or today's date
                    dates = [""] * len(df)
            
            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Found {len(last_names)} clients to upload")
            
            # Initialize Selenium and login to IPS (same as ISWS but different URL)
            webdriver, _By, _WebDriverWait, _EC, _Keys, Service, ChromeDriverManager = _lazy_import_selenium()
            
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            
            try:
                service = Service(ChromeDriverManager().install())
            except:
                service = Service()
            
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 20)
            
            # Login to TherapyNotes IPS (different URL)
            self.log_ips_uploader(_ts() + "[IPS-UPLOADER] Logging into TherapyNotes IPS...")
            driver.get("https://www.therapynotes.com/app/login/IntegrityIPS/")
            time.sleep(3)
            
            # Login logic (same as ISWS uploader)
            username_field = None
            for by, sel in [(By.ID, "Login__UsernameField"), (By.NAME, "username"), (By.ID, "Username"), (By.XPATH, "//input[@type='text']")]:
                try:
                    username_field = wait.until(EC.element_to_be_clickable((by, sel)))
                    break
                except:
                    continue
            
            if not username_field:
                raise Exception("Could not find username field")
            
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", username_field)
            time.sleep(0.3)
            username_field.click()
            time.sleep(0.2)
            username_field.clear()
            username_field.send_keys(self.ips_tn_username.get())
            self.log_ips_uploader(_ts() + "[IPS-UPLOADER] Entered username")
            time.sleep(0.3)
            
            password_field = None
            for by, sel in [(By.ID, "Login__Password"), (By.NAME, "Password"), (By.XPATH, "//input[@type='password']")]:
                try:
                    password_field = wait.until(EC.element_to_be_clickable((by, sel)))
                    break
                except:
                    continue
            
            if not password_field:
                raise Exception("Could not find password field")
            
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", password_field)
            time.sleep(0.3)
            password_field.click()
            time.sleep(0.2)
            password_field.send_keys(self.ips_tn_password.get())
            self.log_ips_uploader(_ts() + "[IPS-UPLOADER] Entered password")
            
            login_btn = None
            for by, sel in [(By.ID, "Login__LogInButton"), (By.XPATH, "//button[@type='submit']"), (By.XPATH, "//button[contains(text(), 'Log In')]")]:
                try:
                    login_btn = WebDriverWait(driver, 10).until(
                        lambda d: d.find_element(by, sel) if d.find_element(by, sel).get_attribute("aria-disabled") == "false" else None
                    )
                    break
                except:
                    try:
                        login_btn = driver.find_element(by, sel)
                        if login_btn.is_displayed() and login_btn.get_attribute("aria-disabled") != "true":
                            break
                    except:
                        continue
            
            if not login_btn:
                raise Exception("Could not find enabled login button")
            
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", login_btn)
            time.sleep(0.3)
            login_btn.click()
            self.log_ips_uploader(_ts() + "[IPS-UPLOADER] Clicked login button")
            time.sleep(4)
            
            # Navigate to Patients (same as ISWS)
            def safe_return_to_patients(refresh_first=False):
                """Return to Patients list reliably, optionally refreshing the page first"""
                try:
                    # If refresh is requested, refresh the page first
                    if refresh_first:
                        self.log_ips_uploader(_ts() + "[IPS-UPLOADER][RECOVERY] Refreshing page to recover from stuck state...")
                        driver.refresh()
                        time.sleep(3)  # Wait for page to reload
                    
                    for by, sel in [(By.LINK_TEXT, "Patients"), (By.XPATH, "//a[contains(text(), 'Patients')]"), (By.XPATH, "//a[contains(@href, '/patients')]")]:
                        try:
                            link = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, sel)))
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
                            try:
                                link.click()
                            except:
                                driver.execute_script("arguments[0].click();", link)
                            wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
                            time.sleep(0.4)
                            if refresh_first:
                                self.log_ips_uploader(_ts() + "[IPS-UPLOADER][RECOVERY] Successfully recovered - returned to Patients page")
                            return True
                        except:
                            continue
                    driver.get("https://www.therapynotes.com/app/patients/list")
                    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
                    time.sleep(0.4)
                    if refresh_first:
                        self.log_ips_uploader(_ts() + "[IPS-UPLOADER][RECOVERY] Successfully recovered - navigated to Patients page")
                    return True
                except Exception as e:
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Could not return to Patients page: {e}")
                    return False
            
            self.log_ips_uploader(_ts() + "[IPS-UPLOADER] Navigating to Patients page...")
            safe_return_to_patients()
            
            # Process each client - ONLY upload IPS-prefixed PDFs
            uploaded = 0
            skipped = 0
            successful_uploads = []
            skipped_clients = []
            output_dir = self.ips_uploader_pdf_folder.get()
            
            for i, (first_name, last_name, dob) in enumerate(zip(first_names, last_names, dobs)):
                # Get date for this client if available (from Date column, NOT DOB)
                client_date = dates[i] if i < len(dates) else ""
                if not self.is_running:
                    break
                
                full_name = f"{first_name} {last_name}".strip()
                self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Processing: {full_name}")
                # Debug: Log what date we're using (should be from Date column, not DOB)
                if client_date:
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][DEBUG] Date from Excel Date column: {client_date} (DOB is: {dob})")
                
                # ONLY look for IPS-prefixed PDFs
                # Normalize spaces in names (handle multiple spaces, trailing spaces, etc.)
                first_clean = re.sub(r'\s+', ' ', str(first_name).strip())
                last_clean = re.sub(r'\s+', ' ', str(last_name).strip())
                
                pdf_filename_options = [
                    sanitize_filename(f"IPS {first_clean} {last_clean} Consent NPP.pdf"),
                    sanitize_filename(f"IPS {first_name.strip()} {last_name.strip()} Consent NPP.pdf"),
                    # Also try with original spacing in case PDFs were created with extra spaces
                    sanitize_filename(f"IPS {first_name} {last_name} Consent NPP.pdf"),
                ]
                
                pdf_path = None
                for filename_option in pdf_filename_options:
                    candidate_path = os.path.join(output_dir, filename_option)
                    if os.path.exists(candidate_path):
                        pdf_path = candidate_path
                        break
                
                if not pdf_path:
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] IPS PDF not found for {first_name} {last_name}")
                    # Debug: Log what we're looking for if PDF not found
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][DEBUG] Looking in: {output_dir}")
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][DEBUG] Tried filenames: {pdf_filename_options[:2]}")
                    # List some actual IPS PDFs in the directory for debugging
                    try:
                        actual_pdfs = [f for f in os.listdir(output_dir) if f.endswith('.pdf') and f.upper().startswith('IPS')]
                        if actual_pdfs:
                            sample_pdfs = actual_pdfs[:3]
                            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][DEBUG] Sample IPS PDFs in folder: {sample_pdfs}")
                    except Exception as e:
                        self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][DEBUG] Could not list PDFs: {e}")
                    skipped += 1
                    skipped_clients.append(f"{full_name} - IPS PDF not found")
                    continue
                
                # Use the same upload logic as ISWS uploader (search, click, upload)
                # For brevity, I'll reference the ISWS uploader's logic - it's identical
                # except we're only processing IPS-prefixed PDFs
                try:
                    # Search for patient (same as ISWS)
                    search_box = None
                    for by, sel in [(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName"), (By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']")]:
                        try:
                            search_box = wait.until(EC.element_to_be_clickable((by, sel)))
                            break
                        except:
                            continue
                    
                    if not search_box:
                        self.log_ips_uploader(_ts() + "[IPS-UPLOADER][WARN] Could not find search box - attempting recovery...")
                        # Try to recover by refreshing and returning to Patients
                        if safe_return_to_patients(refresh_first=True):
                            self.log_ips_uploader(_ts() + "[IPS-UPLOADER][RECOVERY] Recovery successful, continuing with next client")
                            skipped += 1
                            skipped_clients.append(f"{full_name} - Could not find search box (recovered)")
                            continue
                        else:
                            self.log_ips_uploader(_ts() + "[IPS-UPLOADER][WARN] Recovery failed, skipping client")
                            skipped += 1
                            skipped_clients.append(f"{full_name} - Could not find search box (recovery failed)")
                            continue
                    
                    search_box.clear()
                    search_box.send_keys(full_name)
                    time.sleep(2)
                    
                    # Wait for dropdown and find the result matching DOB
                    # The dropdown container is ContentBubbleResultsContainer
                    matched_patient = None
                    
                    try:
                        # Wait for the container to appear AND for results to be populated
                        results_container = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "ContentBubbleResultsContainer"))
                        )
                        self.log_ips_uploader(_ts() + "[IPS-UPLOADER] Dropdown container appeared")
                        
                        # Wait a bit more for results to populate
                        time.sleep(0.5)
                        
                        # Try multiple selectors for the results
                        results = []
                        result_selectors = [
                            "div.ui-menu-item",
                            ".ui-menu-item",
                            "li.ui-menu-item",
                            "a.ui-menu-item",
                            "*[class*='menu-item']",
                            "div[class*='result']",
                        ]
                        
                        for sel in result_selectors:
                            # Search within the container, not globally
                            try:
                                results = results_container.find_elements(By.CSS_SELECTOR, sel)
                                if results:
                                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Found {len(results)} results using selector: {sel}")
                                    break
                            except:
                                continue
                        
                        # Also try finding any clickable elements in the container
                        if not results:
                            all_elements = results_container.find_elements(By.TAG_NAME, "*")
                            clickable = [el for el in all_elements if el.is_displayed() and el.text.strip()]
                            if clickable:
                                results = clickable[:5]  # Limit to first 5
                                self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Found {len(results)} clickable elements in container")
                        
                        self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Total results found: {len(results)}")
                        
                        # Look for a result that contains the DOB
                        if dob and dob.strip() and str(dob).strip() != "nan":
                            # Log the DOB we're looking for
                            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Looking for DOB: {dob}")
                            
                            # Normalize DOB format for comparison (handle various formats)
                            dob_str = str(dob).strip()
                            dob_normalized = dob_str.replace('/', '').replace('-', '').replace(' ', '').strip()
                            
                            # Extract year digits (last 2 digits)
                            year_digits = None
                            try:
                                # Try to extract last 2 digits of year
                                parts = re.split(r'[/-]', dob_str)
                                if len(parts) >= 3:
                                    # Check if first part is 4 digits (YYYY-MM-DD format)
                                    if len(parts[0]) == 4:
                                        # ISO format: YYYY-MM-DD or YYYY/MM/DD
                                        year_part = parts[0]  # Year is first part
                                        if len(year_part) == 4:
                                            year_digits = year_part[-2:]  # Last 2 digits of year (e.g., "1960" -> "60")
                                    else:
                                        # American format: MM/DD/YYYY or MM-DD-YYYY
                                        year_part = parts[-1]  # Year is last part
                                        if len(year_part) >= 2:
                                            year_digits = year_part[-2:]
                            except:
                                pass
                            
                            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Normalized DOB: {dob_normalized}, Year: {year_digits}")
                            
                            for result in results:
                                result_text = result.text.strip()
                                # Log each result for debugging
                                self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Checking result: {result_text[:100]}")
                                
                                result_normalized = result_text.replace('/', '').replace('-', '').replace(' ', '').replace(' ', '')
                                
                                # Check if full DOB matches
                                if dob_normalized in result_normalized:
                                    matched_patient = result
                                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Matched by full DOB: {dob}")
                                    break
                                
                                # Check if year digits match
                                if year_digits and year_digits in result_text:
                                    matched_patient = result
                                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Matched by year: {year_digits}")
                                    break
                        
                        # If no DOB match, just take the first result
                        if matched_patient is None and results:
                            matched_patient = results[0]
                            self.log_ips_uploader(_ts() + "[IPS-UPLOADER] No DOB match, selecting first result")
                        
                        if matched_patient:
                            # Click patient - use JavaScript if regular click fails
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", matched_patient)
                                time.sleep(0.3)
                                matched_patient.click()
                            except:
                                # Fallback to JavaScript click
                                driver.execute_script("arguments[0].click();", matched_patient)
                            time.sleep(2)
                            
                            # Wait for any dialogs/modals to appear and close them if needed
                            try:
                                # Check for common dialog/modal close buttons
                                close_selectors = [
                                    (By.XPATH, "//button[contains(@class, 'close')]"),
                                    (By.XPATH, "//button[@aria-label='Close']"),
                                    (By.XPATH, "//button[contains(., '×')]"),
                                    (By.CSS_SELECTOR, ".Dialog button.close"),
                                ]
                                for by, sel in close_selectors:
                                    try:
                                        close_btn = driver.find_element(by, sel)
                                        if close_btn.is_displayed():
                                            driver.execute_script("arguments[0].click();", close_btn)
                                            time.sleep(0.5)
                                            break
                                    except:
                                        continue
                            except:
                                pass
                        else:
                            raise Exception("No results found in dropdown")
                            
                    except Exception as e:
                        self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Could not select patient from dropdown: {e}")
                        skipped += 1
                        skipped_clients.append(f"{full_name} - Could not select from dropdown: {str(e)[:50]}")
                        # Try to recover by refreshing and returning to Patients
                        self.log_ips_uploader(_ts() + "[IPS-UPLOADER][RECOVERY] Attempting recovery after dropdown selection failure...")
                        safe_return_to_patients(refresh_first=True)
                        continue
                        
                except Exception as e:
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Could not search/find patient: {e}")
                    skipped += 1
                    skipped_clients.append(f"{full_name} - Search failed: {str(e)[:50]}")
                    # Try to recover by refreshing and returning to Patients
                    self.log_ips_uploader(_ts() + "[IPS-UPLOADER][RECOVERY] Attempting recovery after search failure...")
                    safe_return_to_patients(refresh_first=True)
                    continue
                    
                # Open Documents tab
                try:
                    docs_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-tab-id='Documents']")))
                    # Try regular click first, fallback to JavaScript
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", docs_tab)
                        time.sleep(0.3)
                        docs_tab.click()
                    except:
                        driver.execute_script("arguments[0].click();", docs_tab)
                    time.sleep(1.5)  # Increased wait time for Documents tab to load
                except Exception as e:
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Could not open Documents tab: {e}")
                    skipped += 1
                    skipped_clients.append(f"{full_name} - Could not open Documents tab: {str(e)[:50]}")
                    # Try to recover by refreshing and returning to Patients
                    self.log_ips_uploader(_ts() + "[IPS-UPLOADER][RECOVERY] Attempting recovery after Documents tab failure...")
                    safe_return_to_patients(refresh_first=True)
                    continue
                
                # Wait for any dialogs to close before trying to open upload dialog
                time.sleep(1)
                
                # Try to close any blocking dialogs
                try:
                    dialog_selectors = [
                        (By.CSS_SELECTOR, ".Dialog"),
                        (By.CSS_SELECTOR, "[class*='Dialog']"),
                        (By.CSS_SELECTOR, "[class*='modal']"),
                    ]
                    for by, sel in dialog_selectors:
                        try:
                            dialogs = driver.find_elements(by, sel)
                            for dialog in dialogs:
                                if dialog.is_displayed():
                                    # Try to find and click close button in dialog
                                    close_btns = dialog.find_elements(By.XPATH, ".//button[contains(@class, 'close') or contains(., '×') or @aria-label='Close']")
                                    for close_btn in close_btns:
                                        if close_btn.is_displayed():
                                            driver.execute_script("arguments[0].click();", close_btn)
                                            time.sleep(0.5)
                                            break
                        except:
                            continue
                except:
                    pass
                
                # Open upload dialog
                try:
                    # Wait for upload button with multiple selectors
                    upload_btn = None
                    upload_selectors = [
                        (By.XPATH, "//button[contains(., 'Upload Patient File')]"),
                        (By.XPATH, "//button[contains(text(), 'Upload')]"),
                        (By.XPATH, "//button[contains(@class, 'upload')]"),
                        (By.ID, "btnUploadPatientFile"),
                    ]
                    
                    for by, sel in upload_selectors:
                        try:
                            upload_btn = wait.until(EC.element_to_be_clickable((by, sel)))
                            if upload_btn.is_displayed():
                                break
                        except:
                            continue
                    
                    if not upload_btn:
                        raise Exception("Upload button not found")
                    
                    # Try to click with JavaScript to avoid interception
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", upload_btn)
                        time.sleep(0.3)
                        # Try regular click first
                        upload_btn.click()
                    except:
                        # Fallback to JavaScript click
                        driver.execute_script("arguments[0].click();", upload_btn)
                    # Wait longer for dialog to fully load
                    time.sleep(2)
                except Exception as e:
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Could not open upload dialog: {e}")
                    skipped += 1
                    skipped_clients.append(f"{full_name} - Could not open upload dialog: {str(e)[:50]}")
                    # Try to recover by refreshing and returning to Patients
                    self.log_ips_uploader(_ts() + "[IPS-UPLOADER][RECOVERY] Attempting recovery after upload dialog failure...")
                    safe_return_to_patients(refresh_first=True)
                    continue
                
                # Fill upload form (EXACTLY like ISWS uploader)
                try:
                    # Date field - use date from Excel Date column (NOT DOB), then try PDF extraction, then today's date
                    date_field = wait.until(EC.element_to_be_clickable((By.ID, "PatientFile__Date")))
                    date_field.clear()
                    
                    # IMPORTANT: Use date from Excel Date column (NOT DOB - DOB is only for patient matching)
                    # client_date should be from the Date column (or extractor log Date column which contains PDF creation date)
                    if client_date and client_date.strip() and client_date.lower() not in ["nan", "none", ""]:
                        # Date from Excel Date column or extractor log - format it properly
                        try:
                            # Try to parse and format the date
                            date_obj = None
                            # Try common date formats
                            date_formats = ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%y", "%m-%d-%y"]
                            for fmt in date_formats:
                                try:
                                    date_obj = DT.strptime(client_date.strip(), fmt)
                                    # Validate the date is reasonable (not malformed like "11/4/125")
                                    if date_obj.year < 1900 or date_obj.year > 2100:
                                        date_obj = None
                                        continue
                                    # Additional check: if the date matches the DOB exactly, it's probably wrong
                                    # (DOB should not be used as document date - document dates are usually recent)
                                    # However, if using extractor log, the Date column is the PDF creation date, not DOB
                                    if dob and dob.strip():
                                        try:
                                            dob_str = str(dob).strip()
                                            # Try to parse DOB and compare
                                            for dob_fmt in date_formats:
                                                try:
                                                    dob_obj = DT.strptime(dob_str, dob_fmt)
                                                    if date_obj == dob_obj:
                                                        # Date matches DOB - this is suspicious
                                                        # But if it's from extractor log, it might be legitimate if DOB was used as date
                                                        # Check if date is recent (likely document date) vs old (likely DOB)
                                                        if date_obj.year < 2000:
                                                            # Old date matching DOB - definitely wrong
                                                            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Date matches DOB and is old ({date_obj.year}) - likely wrong! Date: {client_date}, DOB: {dob}")
                                                            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Skipping Date column value (matches DOB), will try PDF extraction instead")
                                                            date_obj = None
                                                            break
                                                        else:
                                                            # Recent date matching DOB - might be legitimate (e.g., someone born in 2000s)
                                                            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][INFO] Date matches DOB but is recent ({date_obj.year}) - using it as document date")
                                                except:
                                                    continue
                                            if date_obj is None:
                                                break
                                        except:
                                            pass
                                    break
                                except:
                                    continue
                            
                            if date_obj:
                                date_str = date_obj.strftime("%m/%d/%Y")
                                if is_extractor_log:
                                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Using date from extractor log (PDF creation date): {date_str}")
                                else:
                                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Using date from Excel Date column: {date_str}")
                            else:
                                # If parsing fails or date is invalid/matches DOB, try PDF extraction
                                self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Date from Excel column invalid or matches old DOB, trying PDF extraction...")
                                extracted_date = None
                                try:
                                    extracted_date = self._extract_date_from_pdf(pdf_path)
                                except:
                                    pass
                                if extracted_date:
                                    date_str = extracted_date
                                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Using date extracted from PDF: {date_str}")
                                else:
                                    date_str = DT.now().strftime("%m/%d/%Y")
                                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] No valid date found, using today: {date_str}")
                        except Exception as e:
                            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Could not parse date '{client_date}': {e}, trying PDF extraction...")
                            extracted_date = None
                            try:
                                extracted_date = self._extract_date_from_pdf(pdf_path)
                            except:
                                pass
                            if extracted_date:
                                date_str = extracted_date
                                self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Using date extracted from PDF: {date_str}")
                            else:
                                date_str = DT.now().strftime("%m/%d/%Y")
                                self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Using today's date: {date_str}")
                    else:
                        # No date available from Excel Date column, try to extract from PDF
                        try:
                            extracted_date = self._extract_date_from_pdf(pdf_path)
                            if extracted_date:
                                date_str = extracted_date
                                self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Using date extracted from PDF: {date_str}")
                            else:
                                date_str = DT.now().strftime("%m/%d/%Y")
                                self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] No date found, using today's date: {date_str}")
                        except Exception as e:
                            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Could not extract date from PDF: {e}, using today's date")
                            date_str = DT.now().strftime("%m/%d/%Y")
                    
                    date_field.send_keys(date_str)
                    time.sleep(0.2)
                    
                    # File input (using correct ID like ISWS uploader)
                    file_input = wait.until(EC.presence_of_element_located((By.ID, "InputUploader")))
                    file_input.send_keys(os.path.abspath(pdf_path))
                    time.sleep(0.6)
                    
                    # Document name (using correct ID like ISWS uploader)
                    doc_name = wait.until(EC.element_to_be_clickable((By.ID, "PatientFile__DocumentName")))
                    doc_name.clear()
                    doc_name.send_keys(f"{first_name} {last_name} Consent NPP")
                    time.sleep(0.2)
                    
                    # Click away on a blank part of the upload dialog to activate the button
                    self.log_ips_uploader(_ts() + "[IPS-UPLOADER] Clicking away to activate Add Document button...")
                    try:
                        # Try to click on the dialog background or a label
                        # Click on a label element or the dialog container itself
                        dialog_or_label = driver.find_element(By.XPATH, "//label[text()='Patient']")
                        dialog_or_label.click()
                        time.sleep(0.3)
                    except:
                        try:
                            # Try clicking on the dialog container
                            dialog_container = driver.find_element(By.CLASS_NAME, "modal-body")
                            dialog_container.click()
                            time.sleep(0.3)
                        except:
                            # Just send Tab to move focus away
                            from selenium.webdriver.common.keys import Keys
                            doc_name.send_keys(Keys.TAB)
                            time.sleep(0.3)
                    
                    # Click Add Document
                    add_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='button' and @value='Add Document']")))
                    add_btn.click()
                    time.sleep(2)
                    
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] ✓ Uploaded: {full_name}")
                    uploaded += 1
                    successful_uploads.append(full_name)
                except Exception as e:
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Upload failed: {e}")
                    skipped += 1
                    skipped_clients.append(f"{full_name} - Upload failed: {str(e)[:50]}")
                    # Try to recover by refreshing and returning to Patients
                    self.log_ips_uploader(_ts() + "[IPS-UPLOADER][RECOVERY] Attempting recovery after upload failure...")
                    safe_return_to_patients(refresh_first=True)
                    continue
                
                # Return to Patients page for next client
                if i < len(first_names) - 1:  # Don't return on last client
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Returning to Patients page...")
                    safe_return_to_patients()
            
            driver.quit()
            
            # Generate Excel log
            output_dir_log = self.ips_uploader_output_dir.get()
            if not output_dir_log:
                output_dir_log = os.path.join(os.path.expanduser("~"), "Desktop")
            os.makedirs(output_dir_log, exist_ok=True)
            
            log_rows = []
            for client in successful_uploads:
                log_rows.append({'Client Name': client, 'Status': 'Uploaded', 'Reason': 'Success'})
            for client_reason in skipped_clients:
                if ' - ' in client_reason:
                    client_name, reason = client_reason.split(' - ', 1)
                else:
                    client_name = client_reason
                    reason = 'Unknown'
                log_rows.append({'Client Name': client_name, 'Status': 'Skipped', 'Reason': reason})
            
            if log_rows:
                try:
                    timestamp = DT.now().strftime("%Y%m%d_%H%M%S")
                    log_path = os.path.join(output_dir_log, f"IPS_Uploader_Log_{timestamp}.xlsx")
                    df_log = pd.DataFrame(log_rows)
                    df_log.to_excel(log_path, index=False)
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Excel log saved: {log_path}")
                except Exception as e:
                    self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][WARN] Failed to save log: {e}")
            
            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER] Complete! Uploaded: {uploaded}, Skipped: {skipped}")
            self.ips_uploader_start_btn.config(state="normal")
            self.ips_uploader_stop_btn.config(state="disabled")
            self.is_running = False
            
        except Exception as e:
            self.log_ips_uploader(_ts() + f"[IPS-UPLOADER][ERR] {e}")
            import traceback
            self.log_ips_uploader(traceback.format_exc())
            self.ips_uploader_start_btn.config(state="normal")
            self.ips_uploader_stop_btn.config(state="disabled")
            self.is_running = False
    
    def log_ips_uploader(self, message):
        self.ips_uploader_log_text.insert(tk.END, message + "\n")
        self.ips_uploader_log_text.see(tk.END)
        self.root.update_idletasks()


if __name__ == "__main__":
    root = tk.Tk()
    app = ConsentBotGUI(root)
    root.mainloop()

