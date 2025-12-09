#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISWS Welcome Packet Uploader — v14 Style (Fixed Login + Blur Click + Recursive)
-------------------------------------------------------------------------------
Exact TherapyNotes login using consent-bot IDs:
  URL: https://www.therapynotes.com/app/login/IntegritySWS/
  Username ID: Login__UsernameField
  Password ID: Login__Password
  Login btn ID: Login__LogInButton

Workflow:
  Patients → search by client name (from PDF file name) → Documents → Upload Patient File
  Set Document Name = filename (no extension). Leave date as default (today).
  BLUR FIX: After typing name, click <h2>Upload a Patient File</h2> to enable Add Document.
  Only upload PDFs whose name includes all: welcome + packet + letter (any order, case-insensitive).
  Start/Stop, Add Folder (optional recursive), Excel report.
"""
import os, re, sys, time, threading, queue
from typing import List, Tuple
from datetime import datetime

# GUI
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox

APP_TITLE = "ISWS Welcome Packet Uploader"
TN_LOGIN_URL = "https://www.therapynotes.com/app/login/IntegritySWS/"
MAROON = "#800000"
CARD_BG = "#faf7f7"
LOG_BG  = "#f5f5f5"
LOG_FG  = "#000000"

# ---- UI Logger ----
class UILog:
    def __init__(self, text_widget: scrolledtext.ScrolledText):
        self.text = text_widget
        self.q = queue.Queue()
        self.text.after(80, self._flush)
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
                    sys.stdout.write(line + "\n")
        finally:
            self.text.after(120, self._flush)

# ---- Selenium lazy import ----
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
        raise RuntimeError(f"Missing Selenium packages: {e}\nInstall with: pip install selenium webdriver-manager")
    return webdriver, _By, _WebDriverWait, _EC, Service, ChromeDriverManager

# ---- File helpers ----
PACKET_TOKENS = ("welcome", "packet", "letter")
def is_welcome_packet_letter(filename: str) -> bool:
    if not filename: 
        return False
    try:
        name = os.path.basename(filename).lower() if filename else ""
        if not name: 
            return False
        return name.endswith(".pdf") and all(tok in name for tok in PACKET_TOKENS)
    except Exception:
        return False

COMMON_SUFFIXES = [
    r"\bwelcome\s*packet\s*letter\b",
    r"\bwelcome\b", r"\bpacket\b", r"\bletter\b",
    r"\bfinal\b", r"\bsigned\b", r"\bcomplete\b", r"\bpdf\b"
]
SUFFIX_RX = re.compile(r"(?:%s)[\s_-]*$" % "|".join(COMMON_SUFFIXES), re.I)

def infer_client_name_from_filename(path: str) -> str:
    if not path: return ""
    try:
        base = os.path.basename(path) if path else ""
        if not base or not str(base): return ""
        base_str = str(base)
        if not base_str: return ""
        
        # Remove .pdf extension safely - NO regex if possible
        name = ""
        try:
            # CRITICAL: Ensure base_str is not None and is a string before regex operations
            if not base_str or not isinstance(base_str, str):
                return ""
            # Try regex first - base_str is guaranteed to be a non-empty string
            try:
                name = re.sub(r"\.[Pp][Dd][Ff]$", "", base_str).strip()
            except Exception:
                # If regex fails, just remove .pdf manually
                name = base_str.replace(".pdf", "").replace(".PDF", "").strip()
        except Exception:
            # If everything fails, just return empty
            return ""
        
        if not name or not str(name): return ""
        name_str = str(name)
        if not name_str: return ""
        
        # CRITICAL: Check the whole name FIRST before processing chunks
        # This ensures we get "Eliza Atlas L. King" instead of "L. King"
        try:
            whole_name_result = SUFFIX_RX.sub("", name_str).strip()
            # If whole name has 3+ words, ALWAYS use it (full name with middle)
            if whole_name_result and len(whole_name_result.split()) >= 3:
                return whole_name_result  # Return immediately - this is the full name
        except Exception:
            pass
        
        # Split on delimiters, but filter out empty strings
        chunks = []
        try:
            # CRITICAL: Ensure name_str is not None and is a string before regex operations
            if not name_str or not isinstance(name_str, str):
                return ""
            if not name_str.strip():
                return ""
            # Now safe to use regex - name_str is guaranteed to be a non-empty string
            # CRITICAL: Double-check name_str is valid right before regex call
            if not name_str or not isinstance(name_str, str) or not name_str.strip():
                chunks = []
            else:
                try:
                    split_result = re.split(r"[\\-_]+|\\s{2,}|\\s+–\\s+|\\s+—\\s+|\\s*\\(|\\)|\\[|\\]", name_str)
                    # Filter out None and empty strings - be extra careful
                    if split_result:
                        chunks = [ch for ch in split_result if ch is not None and isinstance(ch, str) and ch.strip()]
                    else:
                        chunks = []
                except Exception:
                    chunks = []
        except Exception:
            chunks = []
        
        # FIRST: Try to reconstruct the full name by joining chunks that look like name parts
        # This handles cases like "Eliza _Atlas_ L. King" where underscores split the name
        name_parts = []
        for ch in chunks:
            if ch is None: continue
            try:
                ch_str = str(ch).strip() if isinstance(ch, str) else str(ch).strip() if ch else ""
                if not ch_str: continue
                # If chunk starts with capital letter, it's likely a name part
                if ch_str and ch_str[0].isupper():
                    # Remove suffixes but keep the name part
                    try:
                        cand = SUFFIX_RX.sub("", ch_str).strip()
                        if cand and len(cand.split()) > 0:
                            name_parts.append(cand)
                    except Exception:
                        if ch_str.strip():
                            name_parts.append(ch_str.strip())
            except Exception:
                continue
        
        # If we have 3+ name parts, join them to form the full name
        if len(name_parts) >= 3:
            full_name_attempt = " ".join(name_parts)
            # Remove any remaining suffixes
            try:
                full_name_attempt = SUFFIX_RX.sub("", full_name_attempt).strip()
            except Exception:
                pass
            if full_name_attempt and len(full_name_attempt.split()) >= 3:
                return full_name_attempt
        
        # If we have 2+ name parts, also try joining them (might be first + last with middle in one chunk)
        if len(name_parts) >= 2:
            # Check if any individual part has 2+ words (might be "L. King" or similar)
            for part in name_parts:
                if len(part.split()) >= 2:
                    # If we have a part with 2+ words AND other parts, join them
                    if len(name_parts) >= 2:
                        joined = " ".join(name_parts)
                        try:
                            joined = SUFFIX_RX.sub("", joined).strip()
                        except Exception:
                            pass
                        if joined and len(joined.split()) >= 3:
                            return joined
        
        # SECOND: Try to find the best candidate from individual chunks
        # Prefer chunks that start with a capital letter (likely first names)
        # and have 3+ words (full names with middle initials/names)
        best_candidate = None
        best_score = 0
        
        for ch in chunks:
            if ch is None: continue
            try:
                # CRITICAL: Ensure ch is not None and is a string before regex operations
                if not isinstance(ch, str):
                    ch_str = str(ch) if ch is not None else ""
                else:
                    ch_str = ch
                if not ch_str or not isinstance(ch_str, str) or not ch_str.strip(): 
                    continue
                # Now safe to use regex - ch_str is guaranteed to be a non-empty string
                try:
                    cand = SUFFIX_RX.sub("", ch_str).strip()
                except Exception:
                    continue
                if cand:
                    word_count = len(cand.split())
                    # Score: prefer chunks that start with capital (first names) and have more words
                    score = 0
                    if word_count >= 3:
                        score += 20  # STRONGLY prefer full names with middle initials/names
                    if word_count >= 2:
                        score += 5   # Minimum acceptable
                    if cand and cand[0].isupper():
                        score += 3   # Bonus for starting with capital (likely first name)
                    
                    if score > best_score:
                        best_score = score
                        best_candidate = cand
            except Exception:
                continue
        
        # CRITICAL: Check the whole name FIRST before returning any chunks
        # This ensures we get "Eliza Atlas L. King" instead of "L. King"
        whole_name_result = None
        try:
            if name_str and isinstance(name_str, str) and name_str.strip():
                # Remove suffixes but keep the full name
                whole_name_result = SUFFIX_RX.sub("", name_str).strip()
                # If whole name has 3+ words, ALWAYS use it (full name with middle)
                if whole_name_result and len(whole_name_result.split()) >= 3:
                    return whole_name_result  # Return immediately - this is the full name
        except Exception:
            pass
        
        # If we found a good candidate with 3+ words, return it immediately
        if best_candidate and best_score >= 20:
            return best_candidate
        
        # If no good chunk found, try joining adjacent chunks that look like names
        # This handles cases like "Eliza _Atlas_ L. King" where underscores split the name
        if len(chunks) >= 2:
            # Try joining chunks that start with capital letters
            joined_chunks = []
            for i, ch in enumerate(chunks):
                if ch and isinstance(ch, str) and ch.strip():
                    ch_str = ch.strip()
                    # If this chunk starts with a capital, it might be part of a name
                    if ch_str and ch_str[0].isupper():
                        joined_chunks.append(ch_str)
                        # Try joining with next chunk if it looks like a name part
                        if i + 1 < len(chunks) and chunks[i + 1]:
                            next_ch = str(chunks[i + 1]).strip()
                            if next_ch and (next_ch[0].isupper() or next_ch[0].isdigit()):
                                # Join them
                                joined = f"{ch_str} {next_ch}"
                                joined_chunks.append(joined)
            
            # Try each joined candidate
            for joined in joined_chunks:
                try:
                    cand = SUFFIX_RX.sub("", joined).strip()
                    if cand and len(cand.split()) >= 2:
                        word_count = len(cand.split())
                        # Prefer longer names (3+ words)
                        if word_count >= 3:
                            return cand  # Return immediately if we found full name
                        elif word_count >= 2 and not best_candidate:
                            best_candidate = cand
                except Exception:
                    continue
        
        # If whole name has 2+ words, prefer it over 2-word chunks
        if whole_name_result and len(whole_name_result.split()) >= 2:
            # Only return 2-word chunks if whole name also has exactly 2 words
            if best_candidate and len(best_candidate.split()) >= 3:
                return best_candidate  # 3-word chunk is better than 2-word whole name
            # Prefer whole name over 2-word chunks
            return whole_name_result
        
        # If we found a good candidate with 2+ words, return it (but only if whole name didn't work)
        if best_candidate and best_score >= 5:
            return best_candidate
        
        # Otherwise return whole name or best candidate
        return whole_name_result if whole_name_result else (best_candidate if best_candidate else "")
    except Exception as e:
        return ""

def first_last_display(name: str) -> str:
    """
    Extract display name from full name.
    For names with 3+ parts (first middle last), return full name.
    For names with 2 parts, return as-is.
    This preserves middle initials/names which are important for search.
    """
    if not name: return ""
    try:
        name_str = str(name) if name else ""
        # CRITICAL: Ensure name_str is not None and is a string before regex operations
        if not name_str or not isinstance(name_str, str):
            return ""
        if not name_str.strip():
            return ""
        # Now safe to use regex - name_str is guaranteed to be a non-empty string
        try:
            # Extract all name tokens (preserve initials like "L.")
            # Updated regex to capture initials with periods: "L." -> ["L."]
            tokens = re.findall(r"[A-Za-z]+\.?|\.", name_str)
            # Filter out just periods
            tokens = [t for t in tokens if t != "."]
            if not tokens: 
                return name_str.strip() if name_str else ""
            # Count words (split by spaces) to determine if we have a full name
            word_count = len(name_str.split())
            # If we have 3+ words, ALWAYS return full name (preserves middle name/initial)
            if word_count >= 3:
                return name_str.strip()  # Return full name for better matching
            # If 3+ tokens (even if some are initials), return full name
            if len(tokens) >= 3:
                return name_str.strip()  # Return full name for better matching
            # If 2 tokens, return first and last
            elif len(tokens) == 2:
                return f"{tokens[0]} {tokens[1]}"
            # If 1 token, return as-is
            else:
                return tokens[0] if tokens else name_str.strip()
        except Exception:
            # If regex fails, just return the name as-is
            return name_str.strip() if name_str else ""
    except Exception:
        return ""

# ---- Selenium helpers ----
def safe_click(wait, locator, driver, desc="element", timeout=12):
    try:
        el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
        try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        except Exception: pass
        try: el.click()
        except Exception: driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        return False

def safe_return_to_patients(wait, driver):
    try:
        link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "Patients")))
        try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
        except Exception: pass
        try: link.click()
        except Exception: driver.execute_script("arguments[0].click();", link)
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
        time.sleep(0.4)
        return True
    except Exception:
        try:
            driver.get("https://www.therapynotes.com/app/patients/list")
            WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
            time.sleep(0.4)
            return True
        except Exception:
            return False

def open_documents_tab(wait, driver):
    locators = [
        (By.CSS_SELECTOR, "a[data-tab-id='Documents']"),
        (By.XPATH, "//a[@data-tab-id='Documents']"),
        (By.XPATH, "//a[normalize-space(text())='Documents']"),
    ]
    for by, sel in locators:
        if safe_click(wait, (by, sel), driver, desc="Documents tab"):
            try:
                WebDriverWait(driver, 12).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Documents')]")),
                        EC.presence_of_element_located((By.XPATH, "//span[contains(@class,'documentNameSpan')]")),
                        EC.presence_of_element_located((By.XPATH, "//table[contains(., 'Document')]"))
                    )
                ); time.sleep(0.4)
                return True
            except Exception:
                pass
    return False

def open_upload_dialog(wait, driver):
    if not open_documents_tab(wait, driver):
        return False
    locators = [
        (By.XPATH, "//button[.//span[contains(@class,'upload')] and contains(normalize-space(.), 'Upload Patient File')]"),
        (By.XPATH, "//button[contains(normalize-space(.), 'Upload Patient File')]"),
        (By.XPATH, "//button[contains(., 'Upload')]"),
    ]
    for by, sel in locators:
        try:
            btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, sel)))
            try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            except Exception: pass
            try: btn.click()
            except Exception: driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.6); return True
        except Exception:
            continue
    return False

def select_patient_by_name(wait, driver, full_name, allow_loose=True, timeout=12):
    import re as _re, time as _time
    def norm(s):
        if s is None: return ""
        try:
            s_str = str(s) if s else ""
            if not s_str or not isinstance(s_str, str): return ""
            s_str = s_str.lower() if s_str else ""
            if not s_str: return ""
            # CRITICAL: Ensure s_str is not None and is a string before regex operations
            if not s_str or not isinstance(s_str, str):
                return ""
            try:
                s_str = _re.sub(r"[^a-z0-9 ]+"," ", s_str)
            except Exception:
                return s_str if s_str else ""
            if not s_str or not isinstance(s_str, str): return ""
            try:
                s_str = _re.sub(r"\s+"," ", s_str)
            except Exception:
                return s_str if s_str else ""
            return s_str.strip() if s_str else ""
        except Exception:
            return ""
    def tokens_in_order(cand, toks):
        pos=0
        for tok in toks:
            i=cand.find(tok, pos)
            if i==-1: return False
            pos=i+len(tok)
        return True
    
    # Helper to remove middle initials/names from name
    def remove_middle_initials(name):
        """
        Remove middle initials/names from name.
        Examples:
        - 'John H. Smith' -> 'John Smith'
        - 'Eliza Atlas L. King' -> 'Eliza King'
        - 'John MiddleName Smith' -> 'John Smith'
        """
        if not name: return ""
        try:
            name_str = str(name) if name else ""
            # CRITICAL: Ensure name_str is not None and is a string before regex operations
            if not name_str or not isinstance(name_str, str):
                return ""
            if not name_str.strip():
                return ""
            # Split into parts
            parts = name_str.split()
            if len(parts) <= 2:
                # Already first and last, return as-is
                return name_str.strip()
            # If 3+ parts, keep first and last, remove middle parts
            # This handles: "Eliza Atlas L. King" -> "Eliza King"
            first = parts[0]
            last = parts[-1]
            return f"{first} {last}".strip()
        except Exception:
            # If anything fails, try regex fallback
            try:
                # Try to remove middle initials like 'H.' or 'H'
                cleaned = _re.sub(r'\s+[A-Z]\.?\s+', ' ', name_str)
                return cleaned.strip() if cleaned else ""
            except Exception:
                # If regex fails, just return the name as-is
                return name_str.strip() if name_str else ""
    
    # CRITICAL: Ensure full_name is valid before processing
    if full_name is None:
        return False
    try:
        full_name_str = str(full_name) if full_name else ""
        if not full_name_str or not full_name_str.strip():
            return False
    except Exception:
        return False
    
    target_norm = norm(full_name_str)
    toks = [t for t in target_norm.split(" ") if t] if target_norm else []
    
    def try_search(search_name):
        """Try searching with a specific name variant"""
        # CRITICAL: Ensure search_name is valid before processing
        if search_name is None:
            return False
        try:
            search_name_str = str(search_name) if search_name else ""
            if not search_name_str or not isinstance(search_name_str, str) or not search_name_str.strip():
                return False
        except Exception:
            return False
        
        candidates = []
        search_norm = ""
        search_toks = []
        try:
            sb = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
            sb.clear(); sb.send_keys(search_name_str); _time.sleep(1.0)
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "ContentBubbleResultsContainer"))); _time.sleep(0.3)
            candidates = driver.find_elements(By.CSS_SELECTOR, "#ContentBubbleResultsContainer > div") or []
            
            try:
                # CRITICAL: Ensure search_name_str is valid before calling norm()
                if not search_name_str or not isinstance(search_name_str, str):
                    return False
                search_norm = norm(search_name_str)
                if not search_norm or not isinstance(search_norm, str):
                    search_norm = ""
            except Exception:
                search_norm = ""
            search_toks = [t for t in search_norm.split(" ") if t] if search_norm else []
        except Exception:
            return False
        
        # Try exact match first
        for rdiv in candidates:
            try:
                text = rdiv.text if hasattr(rdiv, 'text') else None
                if text is None: continue
                # CRITICAL: Ensure text is valid before calling norm()
                try:
                    text_str = str(text) if text else ""
                    if not text_str or not isinstance(text_str, str):
                        continue
                    cand = norm(text_str)
                    if not cand or not isinstance(cand, str):
                        continue
                except Exception:
                    continue
                if cand == search_norm:
                    try: rdiv.click()
                    except Exception: driver.execute_script("arguments[0].click();", rdiv)
                    _time.sleep(0.6); return True
            except Exception: continue
        
        # Try token-based matching
        if allow_loose:
            for rdiv in candidates:
                try:
                    text = rdiv.text if hasattr(rdiv, 'text') else None
                    if text is None: continue
                    # CRITICAL: Ensure text is valid before calling norm()
                    try:
                        text_str = str(text) if text else ""
                        if not text_str or not isinstance(text_str, str):
                            continue
                        cand = norm(text_str)
                        if not cand or not isinstance(cand, str):
                            continue
                    except Exception:
                        continue
                    if tokens_in_order(cand, search_toks):
                        try: rdiv.click()
                        except Exception: driver.execute_script("arguments[0].click();", rdiv)
                        _time.sleep(0.6); return True
                except Exception: continue
        
        # Try partial matching
        for rdiv in candidates:
            try:
                text = rdiv.text if hasattr(rdiv, 'text') else None
                if text is None: continue
                # CRITICAL: Ensure text is valid before calling norm()
                try:
                    text_str = str(text) if text else ""
                    if not text_str or not isinstance(text_str, str):
                        continue
                    cand = norm(text_str)
                    if not cand or not isinstance(cand, str):
                        continue
                except Exception:
                    continue
                if cand.startswith(search_norm) or search_norm in cand:
                    try: rdiv.click()
                    except Exception: driver.execute_script("arguments[0].click();", rdiv)
                    _time.sleep(0.6); return True
            except Exception: continue
        
        return False
    
    # ATTEMPT 1: Try with FULL name (including middle initial/name) - THIS IS THE PRIMARY SEARCH
    try:
        if try_search(full_name_str): 
            return True
    except Exception:
        pass
    
    # ATTEMPT 2: If full name had middle initial/name, try WITHOUT middle initial/name
    # This is the fallback search for browsers with weird search criteria
    name_without_middle = remove_middle_initials(full_name_str)
    if name_without_middle and name_without_middle != full_name_str and name_without_middle.strip():
        try:
            # Clear search box and try without middle initial
            sb = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
            sb.clear()
            _time.sleep(0.3)
            if try_search(name_without_middle):
                return True
        except Exception:
            pass
    
    # ATTEMPT 3: Refresh page and retry with full name
    try:
        driver.refresh()
        WebDriverWait(driver, 12).until(EC.element_to_be_clickable((By.LINK_TEXT, "Patients")))
        driver.find_element(By.LINK_TEXT, "Patients").click()
        _time.sleep(0.8)
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
        _time.sleep(0.4)
        
        if try_search(full_name_str):
            return True
    except Exception:
        pass
    
    # ATTEMPT 4: Final retry without middle initial after refresh
    if name_without_middle and name_without_middle != full_name_str:
        try:
            if try_search(name_without_middle):
                return True
        except Exception:
            pass
    
    # All attempts failed
    return False

# ---- EXACT LOGIN (from consent bot) ----
def tn_login_exact(driver, wait, username: str, password: str, log):
    log("[TN] Opening TherapyNotes…")
    driver.get(TN_LOGIN_URL)
    log("Opening login page…")
    try:
        username_field = wait.until(EC.presence_of_element_located((By.ID, "Login__UsernameField")))
        username_field.clear(); username_field.send_keys(username)
        password_field = wait.until(EC.presence_of_element_located((By.ID, "Login__Password")))
        password_field.clear(); password_field.send_keys(password)
        login_button = wait.until(EC.element_to_be_clickable((By.ID, "Login__LogInButton")))
        login_button.click()
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Patients")))
        log("[TN] Login successful.")
        return True
    except Exception as e:
        log(f"[TN][ERR] Login failed: {e}")
        return False

# ---- Upload one PDF ----
def upload_one_pdf(wait, driver, pdf_path: str, allow_loose: bool, log, stop_event: threading.Event) -> Tuple[bool, str, str]:
    display = "Unknown"
    try:
        if stop_event.is_set(): return False, "", "Stopped by user before processing file"
        if not pdf_path: return False, "", "[SKIP] Empty path provided"
        if os.path.isdir(pdf_path): return False, "", f"[SKIP] Path is a directory, not a file: {pdf_path}"
        if not os.path.isfile(pdf_path): return False, "", f"[SKIP] Missing file: {pdf_path}"
        if not is_welcome_packet_letter(pdf_path): return False, "", "[SKIP] Not a 'Welcome Packet Letter' (ignored)."
        # Get inferred name safely - NO regex operations in error paths
        inferred = ""
        try:
            inferred = infer_client_name_from_filename(pdf_path) or ""
        except Exception as inf_err:
            log(f"[WARN] Could not infer name from filename: {inf_err}")
            inferred = ""
        
        # Get display name safely - NO regex operations in error paths  
        display = "Unknown"
        try:
            if inferred and str(inferred).strip():
                try:
                    display = first_last_display(inferred) or inferred
                except Exception:
                    display = inferred
            else:
                display = os.path.basename(pdf_path) if pdf_path else "Unknown"
        except Exception:
            display = os.path.basename(pdf_path) if pdf_path else "Unknown"
        
        # CRITICAL: Validate inferred name before using it
        if inferred is None:
            return False, display, "[SKIP] Could not infer client name from filename (None)."
        try:
            inferred_str = str(inferred) if inferred else ""
            if not inferred_str or not inferred_str.strip():
                return False, display, "[SKIP] Could not infer client name from filename (empty)."
        except Exception:
            return False, display, "[SKIP] Could not infer client name from filename (invalid)."
        
        try:
            log(f"[TN] Target: {display}  ←  {os.path.basename(pdf_path) if pdf_path else 'Unknown'}")
        except Exception:
            log(f"[TN] Target: {display}")
        
        if not safe_return_to_patients(wait, driver): 
            return False, display, "[ERR] Could not reach Patients list."
        
        try:
            # CRITICAL: Ensure inferred is a valid string before passing to select_patient_by_name
            if not inferred_str or not isinstance(inferred_str, str):
                return False, display, "[SKIP] Invalid inferred name."
            if not select_patient_by_name(wait, driver, inferred_str, allow_loose=True): 
                return False, display, "[SKIP] Patient not found/selected."
        except Exception as e:
            err_msg = str(e) if e else "Unknown error"
            log(f"[WARN] Patient search error for {display}: {err_msg}")
            return False, display, f"[SKIP] Patient search failed: {err_msg[:100]}"
        if not open_upload_dialog(wait, driver): return False, display, "[ERR] Could not open Upload dialog."
        base_no_ext = os.path.splitext(os.path.basename(pdf_path))[0] if pdf_path else ""
        # Set Document Name
        try:
            name_in = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#PatientFile__DocumentName")))
            try: name_in.clear()
            except Exception: pass
            name_in.send_keys(base_no_ext)
            # BLUR FIX: click the dialog header to enable the Save button
            try:
                hdr = WebDriverWait(driver, 6).until(EC.element_to_be_clickable((By.XPATH, "//h2[normalize-space()='Upload a Patient File']")))
                try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", hdr)
                except Exception: pass
                try: hdr.click()
                except Exception: driver.execute_script("arguments[0].click();", hdr)
                time.sleep(0.2)
            except Exception:
                pass
        except Exception:
            pass
        # File chooser
        try:
            file_in = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#InputUploader")))
            file_in.send_keys(os.path.abspath(pdf_path))
        except Exception:
            return False, display, "[ERR] Could not set file path in uploader."
        # Wait for an enabled Add Document button after blur
        try:
            WebDriverWait(driver, 8).until(
                EC.any_of(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='button' and @value='Add Document' and not(@disabled)]")),
                    EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Add Document' and not(@disabled)]")),
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Add') and contains(.,'Document') and not(@disabled)]"))
                )
            )
        except Exception:
            pass
        # Submit
        submitted = False
        for how, what in [
            (By.XPATH, "//input[@type='button' and @value='Add Document' and not(@disabled)]"),
            (By.XPATH, "//button[normalize-space()='Add Document' and not(@disabled)]"),
            (By.XPATH, "//button[contains(.,'Add') and contains(.,'Document') and not(@disabled)]")
        ]:
            try:
                btn = driver.find_element(how, what)
                try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                except Exception: pass
                try: btn.click()
                except Exception: driver.execute_script("arguments[0].click();", btn)
                submitted = True; break
            except Exception:
                continue
        if not submitted: return False, display, "[ERR] Could not click 'Add Document'."
        # Confirmation
        for _ in range(20):
            if stop_event.is_set(): return False, display, "Stopped by user"
            try:
                rows = driver.find_elements(By.CSS_SELECTOR, ".documentNameSpan")
                if any((base_no_ext.lower() in (r.text or '').lower()) for r in rows):
                    return True, display, "Uploaded"
            except Exception: pass
            time.sleep(0.5)
        return False, display, "[WARN] Upload uncertain — no confirmation found."
    except Exception as e:
        log(f"[ERR] Unexpected error processing {display}: {e}")
        return False, display, f"[ERR] Unexpected error: {str(e)[:200]}"

# ---- Excel logging ----
def save_excel_report(rows: List[Tuple[str, str, str]], out_dir: str) -> str:
    try:
        import pandas as pd
    except Exception as e:
        raise RuntimeError("Missing pandas. Please install with: pip install pandas openpyxl") from e
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"WelcomePacketUpload_Log_{ts}.xlsx"
    out_path = os.path.join(out_dir, out_name)
    df = pd.DataFrame(rows, columns=["Client Name", "Upload Date", "Note"])
    df.to_excel(out_path, index=False)
    return out_path

def desktop_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Desktop")

# ---- Worker ----
def run_worker(username: str, password: str, pdfs: List[str], ui_log: UILog, stop_event: threading.Event, report_dir: str):
    write = ui_log.write
    rows: List[Tuple[str,str,str]] = []
    up_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    driver = None
    wait = None
    try:
        try:
            webdriver, _By, _WebDriverWait, _EC, Service, ChromeDriverManager = _lazy_import_selenium()
        except Exception as e:
            messagebox.showerror("Missing dependency", str(e)); return
        global By, WebDriverWait, EC
        By, WebDriverWait, EC = _By, _WebDriverWait, _EC
                
        # Build & filter files
        files = []
        seen = set()
        for p in pdfs:
            if not p: continue
            try:
                ap = os.path.abspath(p)
                if ap.lower() in seen: continue
                seen.add(ap.lower())
                # Skip directories - only process actual PDF files
                if os.path.isdir(ap): continue
                if ap.lower().endswith(".pdf") and os.path.isfile(ap):
                    files.append(ap)
            except Exception:
                continue
        if not files:
            write("[UI] No PDFs queued."); return
        packet_files = []
        for p in files:
            try:
                if is_welcome_packet_letter(p):
                    packet_files.append(p)
            except Exception:
                continue
        skipped = len(files) - len(packet_files)
        if skipped: write(f"[UI] Skipping {skipped} non-'Welcome Packet Letter' PDF(s).")
        if not packet_files:
            write("[UI] No eligible 'Welcome Packet Letter' PDFs found."); return
        # Start Chrome
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 12)
        except Exception as e:
            messagebox.showerror("Chrome error", f"Could not start Chrome: {e}"); return
        try:
            if stop_event.is_set():
                write("[STOP] Cancelled before login."); return
            if not tn_login_exact(driver, wait, username, password, write):
                return
            write(f"[RUN] Uploading {len(packet_files)} 'Welcome Packet Letter'(s)…")
            ok_count = 0
            for idx, path in enumerate(packet_files, 1):
                # OUTERMOST TRY - catch absolutely everything
                try:
                    if stop_event.is_set(): 
                        write("[STOP] Cancelled by user. Ending early.")
                        break
                    
                    # Initialize defaults
                    display_name = "Unknown"
                    success = False
                    display = "Unknown"
                    note = "Unknown error"
                    path_str = str(path) if path else f"File {idx}"
                    
                    # INNER TRY - process the file
                    try:
                        if not path:
                            write(f"[SKIP] File {idx}: Empty path")
                            rows.append(("Unknown", up_date, "[SKIP] Empty path"))
                            continue
                        
                        # Try to upload
                        try:
                            success, display, note = upload_one_pdf(wait, driver, path, True, write, stop_event)
                            # Ensure all values are strings - handle None explicitly
                            success = bool(success) if success is not None else False
                            display = str(display) if display is not None else "Unknown"
                            note = str(note) if note is not None else "Unknown"
                        except Exception as upload_err:
                            # Catch any error in upload_one_pdf
                            # Convert error to string SAFELY - don't use f-strings if error might have issues
                            try:
                                err_msg = str(upload_err) if upload_err is not None else "Unknown upload error"
                            except Exception:
                                err_msg = "Unknown upload error"
                            try:
                                write(f"[ERR] Upload function failed for file {idx}: {err_msg}")
                            except Exception:
                                write("[ERR] Upload function failed")
                            success = False
                            display = "Unknown"
                            try:
                                note = f"[ERR] Upload failed: {err_msg[:100]}" if err_msg else "[ERR] Upload failed"
                            except Exception:
                                note = "[ERR] Upload failed"
                        
                        # Try to get display name safely
                        try:
                            if display and display != "Unknown":
                                display_name = str(display)
                            else:
                                # Try to infer from filename
                                try:
                                    inferred = infer_client_name_from_filename(path) or ""
                                    if inferred:
                                        try:
                                            display_name = first_last_display(inferred) or inferred
                                        except Exception:
                                            display_name = inferred
                                    else:
                                        display_name = os.path.basename(path) if path else f"File {idx}"
                                except Exception:
                                    display_name = os.path.basename(path) if path else f"File {idx}"
                        except Exception:
                            display_name = os.path.basename(path) if path else f"File {idx}"
                        
                        # Add to rows - ensure all values are strings
                        try:
                            rows.append((str(display_name), str(up_date), str(note)))
                            if success: ok_count += 1
                        except Exception:
                            # If even appending fails, just log and continue
                            write(f"[WARN] Could not log result for file {idx}")
                            continue
                            
                    except Exception as inner_e:
                        # Inner exception - log and continue
                        # DO NOT use any regex functions in error handler - just use basic string ops
                        try:
                            # Convert error to string SAFELY
                            try:
                                err_msg = str(inner_e) if inner_e is not None else "Unknown error"
                            except Exception:
                                err_msg = "Unknown error"
                            # Log error SAFELY - don't use f-strings if error formatting might fail
                            try:
                                write(f"[ERR] Error processing file {idx}: {err_msg}")
                            except Exception:
                                write(f"[ERR] Error processing file {idx}")
                            
                            # Get display name using ONLY basic string operations - NO regex functions
                            try:
                                if path:
                                    # Just use basename - don't call infer_client_name_from_filename or first_last_display
                                    # Those functions use regex and could fail again
                                    try:
                                        display_name = os.path.basename(path) if path else f"File {idx}"
                                    except Exception:
                                        display_name = f"File {idx}"
                                else:
                                    display_name = f"File {idx}"
                            except Exception:
                                display_name = f"File {idx}"
                            
                            # Try to add to rows
                            try:
                                rows.append((str(display_name), str(up_date), f"[ERR] {err_msg[:200]}"))
                            except Exception:
                                pass  # If even this fails, just skip
                        except Exception:
                            # If error handler itself fails, just continue silently
                            try:
                                write(f"[CRITICAL] Error handler failed for file {idx}")
                            except Exception:
                                pass  # Even writing failed, just continue
                            continue
                        
                except Exception as outer_e:
                    # OUTERMOST catch - if even the outer try fails, just log and continue
                    # DO NOT use any regex functions here - just basic string ops
                    try:
                        # Convert error to string SAFELY
                        try:
                            err_msg = str(outer_e) if outer_e is not None else "Unknown critical error"
                        except Exception:
                            err_msg = "Unknown critical error"
                        # Log error SAFELY
                        try:
                            write(f"[CRITICAL] Critical error for file {idx}: {err_msg}")
                        except Exception:
                            try:
                                write(f"[CRITICAL] Critical error for file {idx}")
                            except Exception:
                                pass  # Even writing failed
                        try:
                            # Use ONLY basic string operations - no regex functions
                            if path:
                                try:
                                    display_name = os.path.basename(str(path))
                                except Exception:
                                    display_name = f"File {idx}"
                            else:
                                display_name = f"File {idx}"
                        except Exception:
                            display_name = f"File {idx}"
                        try:
                            rows.append((str(display_name), str(up_date), f"[CRITICAL] {err_msg[:200]}"))
                        except Exception:
                            pass  # If even this fails, just skip the file
                    except Exception:
                        # If even the critical handler fails, just continue silently
                        pass
                    continue  # Continue to next file no matter what
                
            write(f"[DONE] Completed. Success: {ok_count}/{len(packet_files)}")
        except Exception as fatal_error:
            # Ultimate catch-all for entire worker function
            write(f"[FATAL] Fatal error in worker: {fatal_error}")
            import traceback
            write(f"[FATAL] Traceback: {traceback.format_exc()}")
    finally:
        try: 
            if driver:
                driver.quit()
        except Exception: pass
    # Save Excel
    try:
        out_dir = report_dir or desktop_dir()
        os.makedirs(out_dir, exist_ok=True)
        out_path = save_excel_report(rows, out_dir)
        write(f"[REPORT] Excel saved → {out_path}")
    except Exception as e:
        write(f"[REPORT][ERR] Could not write Excel: {e}")

# ---- GUI ----
class App:
    def __init__(self, root):
        self.root = root
        root.title(f"{APP_TITLE} - Version 2.1.0, Last Updated 12/03/2025")
        root.geometry("1040x800")
        style = ttk.Style()
        try: style.theme_use('clam')
        except Exception: pass
        style.configure('TLabel', background=MAROON, foreground='#ffffff', font=("Helvetica", 11))
        style.configure('Header.TLabel', font=("Helvetica", 20, 'bold'))
        style.configure('Card.TFrame', background=CARD_BG)
        style.configure('TButton', font=("Helvetica", 11, 'bold'))

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.include_recursive = tk.BooleanVar(value=True)
        self.report_dir = tk.StringVar(value="")
        self.files: List[str] = []
        self.worker_thread = None
        self.stop_event = threading.Event()

        header = ttk.Label(root, text=APP_TITLE, style="Header.TLabel")
        header.pack(pady=(12,6), fill='x')

        def card(parent):
            f = ttk.Frame(parent, style='Card.TFrame'); f.configure(padding=(14,12)); return f

        creds_card = card(root); creds_card.pack(fill='x', padx=12, pady=(6,6))
        ttk.Label(creds_card, text="TN Username:", background=CARD_BG, foreground="#000000").grid(row=0, column=0, sticky='e', padx=(0,8))
        ttk.Entry(creds_card, textvariable=self.username, width=32).grid(row=0, column=1, sticky='w')
        ttk.Label(creds_card, text="TN Password:", background=CARD_BG, foreground="#000000").grid(row=1, column=0, sticky='e', padx=(0,8))
        ttk.Entry(creds_card, textvariable=self.password, show='*', width=32).grid(row=1, column=1, sticky='w')

        files_card = card(root); files_card.pack(fill='x', padx=12, pady=(6,6))
        ttk.Button(files_card, text="Add PDFs…", command=self.add_pdfs).grid(row=0, column=0, sticky='w')
        ttk.Button(files_card, text="Add Folder…", command=self.add_folder).grid(row=0, column=1, sticky='w', padx=(8,0))
        ttk.Checkbutton(files_card, text="Include subfolders (recursive)", variable=self.include_recursive).grid(row=0, column=2, sticky='w', padx=(12,0))
        ttk.Button(files_card, text="Clear List", command=self.clear_list).grid(row=0, column=3, sticky='w', padx=(12,0))
        ttk.Label(files_card, text="Excel output folder (optional):", background=CARD_BG, foreground="#000000").grid(row=1, column=0, sticky='e', pady=(10,0))
        ttk.Entry(files_card, textvariable=self.report_dir, width=50).grid(row=1, column=1, sticky='w', pady=(10,0))
        ttk.Button(files_card, text="Browse…", command=self.pick_report_dir).grid(row=1, column=2, sticky='w', pady=(10,0), padx=(6,0))
        self.file_count = ttk.Label(files_card, text="Queued: 0 (packet letters only at run time)", background=CARD_BG, foreground="#000000")
        self.file_count.grid(row=0, column=4, sticky='w', padx=(16,0))

        controls_card = card(root); controls_card.pack(fill='x', padx=12, pady=(6,6))
        self.start_btn = ttk.Button(controls_card, text="Start", command=self.start_run, width=16)
        self.stop_btn  = ttk.Button(controls_card, text="Stop", command=self.stop_run, width=16)
        self.start_btn.grid(row=0, column=0, padx=(0,8))
        self.stop_btn.grid(row=0, column=1)
        ttk.Label(controls_card, text="Status:", background=CARD_BG, foreground="#000000").grid(row=0, column=2, padx=(16,6))
        self.status_lbl = ttk.Label(controls_card, text="Idle", background=CARD_BG, foreground="#000000")
        self.status_lbl.grid(row=0, column=3, sticky='w')

        log_card = card(root); log_card.pack(fill='both', expand=True, padx=12, pady=(6,12))
        self.log = scrolledtext.ScrolledText(log_card, width=120, height=26, bg=LOG_BG, fg=LOG_FG, font=("Consolas", 10))
        self.log.pack(fill='both', expand=True)
        self.uilog = UILog(self.log)

    # --- helpers ---
    def _update_count(self):
        self.file_count.configure(text=f"Queued: {len(self.files)} (packet letters only at run time)")
    def _dedupe_preserve_order(self):
        seen=set(); uniq=[]
        for p in self.files:
            if p not in seen: uniq.append(p); seen.add(p)
        self.files=uniq

    # --- File pickers ---
    def add_pdfs(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        if paths:
            self.files.extend(list(paths))
            self._dedupe_preserve_order(); self._update_count()
            self.uilog.write("[UI] Added PDF(s).")
    def add_folder(self):
        d = filedialog.askdirectory()
        if not d: return
        added = 0
        for rootdir, _dirs, files in os.walk(d):
            for name in files:
                if name.lower().endswith('.pdf'):
                    full_path = os.path.join(rootdir, name)
                    # Only add actual files, not directories
                    if os.path.isfile(full_path):
                        self.files.append(full_path)
                        added += 1
            if not self.include_recursive.get():
                break
        if added == 0:
            messagebox.showinfo("No PDFs", "No .pdf files found in the selected folder{0}.".format(" (and subfolders)" if self.include_recursive.get() else ""))
        self._dedupe_preserve_order(); self._update_count()
        self.uilog.write(f"[UI] Added {added} PDF(s) from folder{' (recursive)' if self.include_recursive.get() else ''}.")
    def clear_list(self):
        self.files.clear(); self._update_count(); self.uilog.write("[UI] Cleared queue.]")
    def pick_report_dir(self):
        d = filedialog.askdirectory()
        if d: self.report_dir.set(d)

    # --- Start/Stop ---
    def start_run(self):
        if hasattr(self, "worker_thread") and self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("Busy", "A run is already in progress."); return
        if not self.username.get().strip() or not self.password.get().strip():
            messagebox.showwarning("Missing login", "Enter your TherapyNotes username and password."); return
        if not self.files:
            messagebox.showinfo("Nothing queued", "Add PDFs to upload first."); return
        self.stop_event = threading.Event()
        self.status_lbl.configure(text="Running…")
        self.uilog.write("[RUN] Started.")
        args = (
            self.username.get().strip(),
            self.password.get().strip(),
            list(self.files),
            self.uilog,
            self.stop_event,
            self.report_dir.get().strip()
        )
        self.worker_thread = threading.Thread(target=run_worker, args=args, daemon=True)
        self.worker_thread.start()
        self.root.after(500, self._poll_done)
    def _poll_done(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.root.after(500, self._poll_done)
        else:
            self.status_lbl.configure(text="Idle")
            self.uilog.write("[RUN] Finished.")
    def stop_run(self):
        if hasattr(self, "stop_event") and self.worker_thread and self.worker_thread.is_alive():
            self.stop_event.set()
            self.uilog.write("[STOP] Requested. The bot will finish the current step and exit.")
        else:
            self.uilog.write("[STOP] No active run.")

# ---- Main ----
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = App(root)
        root.mainloop()
    except Exception as e:
        print("[FATAL] GUI failed to start:", e)
