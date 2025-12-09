# isws_welcome_highlight_batch_NAVPATCH_INSPECT_DEEP.py
# Additive patch: deeper "Extract Page Elements" (smart waits + full HTML + shadow DOM)
# Leaves your Name/Address + nav UI intact.

import os, re, json, time, tempfile, threading, queue, csv
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox

APP_TITLE = "CCMD Extraction Tool"
PN_DEFAULT_URL = "https://integrityseniorservices.athena-us.com/acm_loginControl"
MAROON = "#800000"
LEARN_DB = "learned_pn_selectors.json"  # saved next to this script

# ------------------------ Utilities ------------------------
def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", (name or "").strip())

def desktop_snap_dir():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    out = os.path.join(desktop, "Welcome Bot Snapshots")
    os.makedirs(out, exist_ok=True)
    return out

def normalize_address_lines(lines):
    out = []
    junk = re.compile(
        r"^(main address|address|profile|demographics|policy|messages|client|contact info|prev|edit|next|send welcome letter|npp|welcome letter|case)$",
        re.I
    )
    for ln in lines or []:
        t = " ".join((ln or "").split()).strip()
        if not t:
            continue
        if junk.search(t):
            continue
        t = t.replace("(show map)", "").strip()
        if t:
            out.append(t)
    looks_street = any(re.search(r"\d", ln) for ln in out)
    looks_zip = any(re.search(r"\b\d{5}(?:-\d{4})?\b", ln) for ln in out)
    looks_cityst = any(re.search(r"[A-Za-z]{2}\s*\d{5}", ln) for ln in out)
    if not (looks_street or looks_zip or looks_cityst):
        return []
    seen = set(); clean = []
    for ln in out:
        key = ln.lower()
        if key in seen:
            continue
        seen.add(key)
        clean.append(ln)
    return clean[:4]

def guess_name_from_text(text):
    if not text:
        return ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    killers = re.compile(r"\b(send|welcome|letter|npp|case|general|workflow)\b", re.I)
    for ln in lines:
        if ":" in ln or len(ln) > 64 or killers.search(ln):
            continue
        toks = [t for t in re.split(r"\s+", ln) if re.search(r"[A-Za-z]", t)]
        if 2 <= len(toks) <= 4 and all(re.match(r"^[A-Za-z.\-']+$", t) for t in toks):
            if any(re.match(r"^[A-Z][a-z]+(?:[.\-']?[A-Za-z]+)*$", t) for t in toks):
                return ln
    return ""

# ------------------------ Learn DB (minimal) ------------------------
class LearnDB:
    def __init__(self, path=LEARN_DB):
        self.path = os.path.join(os.getcwd(), path)
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
        self.data[key] = {"css": css, "frame": (frame_hint or {}), "note": note or ""}
        self.save()

    def get(self, key):
        return self.data.get(key) or {}

# ------------------------ JS blocks ------------------------
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

JS_WAIT_COUNT = r"""
return (function(){
  try{
    var n = document.querySelectorAll('a,button,[role="button"],[onclick],input[type="button"],input[type="submit"]').length;
    var t = (document.body && document.body.innerText) ? document.body.innerText.length : 0;
    return {ok:true, clickable:n, textlen:t, url: location.href};
  }catch(e){
    return {ok:false, err: String(e)};
  }
})();
"""

JS_OPEN_DROPDOWNS = r"""
return (function(){
  var opened = 0;
  try {
    // Try to find and open common dropdown triggers
    var triggers = document.querySelectorAll('input[autocomplete], input[list], .dropdown-toggle, [data-toggle="dropdown"], .select2-selection, .chosen-single');
    for (var i = 0; i < triggers.length; i++) {
      try {
        var el = triggers[i];
        // Try different ways to open dropdown
        if (el.click) el.click();
        if (el.focus) el.focus();
        // Trigger events
        var events = ['click', 'focus', 'mousedown', 'mouseup'];
        for (var j = 0; j < events.length; j++) {
          try {
            var event = new Event(events[j], {bubbles: true});
            el.dispatchEvent(event);
          } catch(e) {}
        }
        opened++;
      } catch(e) {}
    }
  } catch(e) {}
  return {opened: opened};
})();
"""

JS_SNAPSHOT_DEEP = r"""
return (function(){
 function cssPath(el){
  if (!el) return null; if (el.id) return '#'+el.id;
  var path=[], node=el, depth=0;
  while(node && node.nodeType===1 && depth<8){
    var sel=node.tagName.toLowerCase();
    if (node.id){ sel+='#'+node.id; path.unshift(sel); break; }
    var idx=1, sib=node; while((sib=sib.previousElementSibling)!=null){ if (sib.tagName===node.tagName) idx++; }
    sel+=':nth-of-type('+idx+')'; path.unshift(sel); node=node.parentElement; depth++;
  }
  return path.join(' > ');
 }
 function isVisible(el){
   var st=getComputedStyle(el);
   if (st.display==='none' || st.visibility==='hidden' || parseFloat(st.opacity)===0) return false;
   var r=el.getBoundingClientRect();
   return r.width>2 && r.height>2;
 }
 function clickable(el){
   if (!isVisible(el)) return false;
   var t=(el.tagName||'').toLowerCase();
   if (t==='a'||t==='button') return true;
   var ty=(el.getAttribute('type')||'').toLowerCase();
   if (ty==='button'||ty==='submit') return true;
   if (el.getAttribute('role')==='button') return true;
   if (el.getAttribute('onclick')) return true;
   if (el.tabIndex>=0) return true;
   if (t==='td'||t==='th'||t==='div'){
     if (el.querySelector('a,button,[role=\"button\"],[onclick],input[type=\"button\"],input[type=\"submit\"]')) return true;
   }
   return false;
 }
 // ENHANCED: Special dropdown detection
 function findDropdownOptions(root){
   var dropdowns = [];
   // Look for common dropdown patterns
   var selectors = [
     'ul li', 'div[role=\"listbox\"] div', 'div[role=\"option\"]', 
     'ul[role=\"listbox\"] li', 'ul[role=\"menu\"] li',
     '.dropdown-item', '.select-option', '.autocomplete-item',
     'div.dropdown-content div', 'div.autocomplete div'
   ];
   
   for (var s=0; s<selectors.length; s++){
     var elements = root.querySelectorAll(selectors[s]);
     for (var i=0; i<elements.length; i++){
       var el = elements[i];
       if (!isVisible(el)) continue;
       var text = (el.innerText||el.textContent||'').replace(/\s+/g,' ').trim();
       if (text.length > 0 && text.length < 100) {
         var rect = el.getBoundingClientRect();
         dropdowns.push({
           type: 'dropdown_option',
           selector: selectors[s],
           text: text,
           css: cssPath(el),
           tag: (el.tagName||'').toLowerCase(),
           role: el.getAttribute('role')||'',
           class: el.className||'',
           id: el.id||'',
           rect: {x:Math.round(rect.left), y:Math.round(rect.top), w:Math.round(rect.width), h:Math.round(rect.height)}
         });
       }
     }
   }
   return dropdowns;
 }
 // Traverse simple shadow roots (shallow)
 function enumerateRoots(){
   var roots=[document];
   var nodes = document.querySelectorAll('*');
   for (var i=0;i<nodes.length;i++){
     var sr = nodes[i].shadowRoot;
     if (sr) roots.push(sr);
   }
   return roots;
 }
 var out=[], idx=0, roots=enumerateRoots();
 var limit=2500;
 
 // First pass: Regular elements
 for (var rdx=0; rdx<roots.length; rdx++){
   var root = roots[rdx];
   var nodes = root.querySelectorAll('a,button,[role=\"button\"],[onclick],input[type=\"button\"],input[type=\"submit\"],td,th,div');
   for (var i=0;i<nodes.length && out.length<limit;i++){
     var el=nodes[i]; if (!isVisible(el)) continue;
     var rect=el.getBoundingClientRect();
     var text=(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim().slice(0,160);
     out.push({
       idx: idx++,
       tag: (el.tagName||'').toLowerCase(),
       css: cssPath(el),
       text: text,
       aria: el.getAttribute('aria-label')||'',
       title: el.getAttribute('title')||'',
       href: el.getAttribute('href')||'',
       role: el.getAttribute('role')||'',
       idAttr: el.id||'',
       nameAttr: el.getAttribute('name')||'',
       type: el.getAttribute('type')||'',
       rect: {x:Math.round(rect.left), y:Math.round(rect.top), w:Math.round(rect.width), h:Math.round(rect.height)},
       clickable: clickable(el)
     });
   }
 }
 
 // Second pass: ENHANCED dropdown detection
 var dropdownOptions = [];
 for (var rdx=0; rdx<roots.length; rdx++){
   var root = roots[rdx];
   var dropdowns = findDropdownOptions(root);
   for (var d=0; d<dropdowns.length; d++){
     dropdownOptions.push({
       idx: idx++,
       type: 'DROPDOWN_OPTION',
       ...dropdowns[d]
     });
   }
 }
 
 // Combine results
 out = out.concat(dropdownOptions);
 var html = (document.documentElement && document.documentElement.outerHTML) ? document.documentElement.outerHTML : '';
 return {items: out, url: location.href, html: html, dropdown_count: dropdownOptions.length};
})();
"""

# ------------------------ GUI App (only the inspect button is relevant here) ------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title(f"{APP_TITLE} - Version 2.1.0, Last Updated 12/03/2025")
        root.geometry("980x880")
        root.configure(bg=MAROON)

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

        # Header
        ttk.Label(root, text=APP_TITLE, style="Header.TLabel").pack(pady=(12,6), fill='x')

        def card(parent):
            f = ttk.Frame(parent, style='Card.TFrame'); f.configure(padding=(14,12)); return f

        # --- Browser controls ---
        teach = card(root); teach.pack(fill='x', padx=12, pady=6)
        ttk.Button(teach, text="Open Penelope + Login", command=self.open_pn).grid(row=0, column=0, padx=6, pady=4)
        ttk.Button(teach, text="Reinstall Highlight Hook", command=self.install_highlight_capture).grid(row=0, column=1, padx=10)
        ttk.Button(teach, text="Extract Page Elements (DEEP)", command=self.extract_page_elements_deep).grid(row=0, column=2, padx=6, pady=4)
        
        # Add delay control
        ttk.Label(teach, text="Extraction Delay (seconds):").grid(row=1, column=0, padx=6, pady=4, sticky='e')
        self.extraction_delay = tk.IntVar(value=5)
        delay_spin = ttk.Spinbox(teach, from_=0, to=30, textvariable=self.extraction_delay, width=10)
        delay_spin.grid(row=1, column=1, padx=6, pady=4, sticky='w')
        ttk.Label(teach, text="(Time to open dropdowns before extraction)", style='TLabel', font=("Helvetica", 9)).grid(row=1, column=2, padx=6, pady=4, sticky='w')

        # --- Log ---
        log_card = card(root); log_card.pack(fill='both', expand=True, padx=12, pady=10)
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
                        if not users or not pwds:
                            return False
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
                        p.send_keys(Keys.ENTER)
                        return True
                    except Exception:
                        return False

                if not try_login_in_ctx(self._driver):
                    frames = self._driver.find_elements(By.TAG_NAME, "iframe")
                    ok = False
                    for fr in frames:
                        try:
                            self._driver.switch_to.default_content()
                            self._driver.switch_to.frame(fr)
                            if try_login_in_ctx(self._driver):
                                ok = True
                                break
                        except Exception:
                            continue
                    self._driver.switch_to.default_content()
                    if not ok:
                        self.enqueue("[PN] Could not find login fields.")
                        return

                try:
                    wait.until(EC.any_of(
                        EC.url_changes(url),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'logout')]"))
                    ))
                except Exception:
                    pass

                self.enqueue("[PN] Login appears successful.")
                self.install_highlight_capture()

            except Exception as e:
                self.enqueue(f"[PN][ERROR] {e}")

        threading.Thread(target=worker, daemon=True).start()

    def install_highlight_capture(self):
        if not self._driver:
            return
        try:
            self._driver.switch_to.default_content()
            self._driver.execute_script(JS_INSTALL_CAPTURE)
            frames = self._driver.find_elements("tag name", "iframe")
            for fr in frames:
                try:
                    self._driver.switch_to.default_content()
                    self._driver.switch_to.frame(fr)
                    self._driver.execute_script(JS_INSTALL_CAPTURE)
                except Exception:
                    continue
            self._driver.switch_to.default_content()
        except Exception:
            pass
        self.enqueue("[TEACH] Highlight hook installed. If you change pages, click 'Reinstall Highlight Hook' and try again.")

    # ------------- Deep Extract -------------
    def extract_page_elements_deep(self):
        if not self._driver:
            self.enqueue("[INSPECT] Open Penelope first."); return

        # Get the delay from the UI
        delay_seconds = self.extraction_delay.get()
        
        if delay_seconds > 0:
            self.enqueue(f"[INSPECT] ⏰ COUNTDOWN: {delay_seconds} seconds to open dropdowns...")
            self.enqueue("[INSPECT] → Switch back to the browser and open any dropdowns NOW!")
            
            # Countdown timer
            for i in range(delay_seconds, 0, -1):
                self.enqueue(f"[INSPECT] ⏱️  {i}...")
                time.sleep(1)
            
            self.enqueue("[INSPECT] ✓ Starting extraction now!")
        
        out_dir = desktop_snap_dir()
        ts = time.strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(out_dir, f"page_snapshot_DEEP_{ts}.json")
        csv_path  = os.path.join(out_dir, f"page_snapshot_DEEP_{ts}.csv")

        snap = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "frames": []}

        def snapshot_current_frame(frame_chain, idx_path):
            # Smart wait for content to load
            waited = 0.0
            clickable = 0
            textlen = 0
            url = ""
            for _ in range(30):  # up to ~3s
                res = None
                try:
                    res = self._driver.execute_script(JS_WAIT_COUNT)
                except Exception:
                    res = None
                if res and res.get("ok"):
                    clickable = int(res.get("clickable") or 0)
                    textlen = int(res.get("textlen") or 0)
                    url = res.get("url") or ""
                    if clickable >= 1 or textlen >= 50:
                        break
                time.sleep(0.1); waited += 0.1

            # Note: Manual dropdown opening via countdown delay (disabled automatic opening)
            # User opens dropdown manually during the countdown timer
            dropdowns_opened = 0

            # Snapshot deep
            items = []; html = ""
            dropdown_count = 0
            try:
                res2 = self._driver.execute_script(JS_SNAPSHOT_DEEP)
                if isinstance(res2, dict):
                    items = list(res2.get("items") or [])
                    url = url or (res2.get("url") or "")
                    html = res2.get("html") or ""
                    dropdown_count = int(res2.get("dropdown_count") or 0)
            except Exception as e:
                self.enqueue(f"[INSPECT] JS snapshot failed in frame {frame_chain}: {e}")

            # Save HTML for this frame
            html_path = None
            try:
                html_path = os.path.join(out_dir, f"frame_{idx_path}.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                html_path = None

            meta = {
                "frame_chain": frame_chain, 
                "url": url, 
                "items_count": len(items), 
                "waited": round(waited,2),
                "dropdowns_opened": dropdowns_opened,
                "dropdown_options_found": dropdown_count
            }
            if html_path: meta["html_path"] = html_path

            # Append to global JSON and CSV
            snap["frames"].append(meta)
            return items, meta

        def frame_id_string(chain):
            # Build a stable id like 1_3_0 from indices
            return "_".join(str(m.get("index")) for m in chain) if chain else "root"

        def recurse_frames(chain_prefix):
            # Snapshot this frame
            idxp = frame_id_string(chain_prefix)
            items, meta = snapshot_current_frame(chain_prefix, idxp)

            # Append CSV rows
            try:
                rows = []
                fpath = " > ".join([f"[{m.get('index')}]{m.get('id') or m.get('name') or ''}" for m in (meta["frame_chain"] or [])])
                for it in items[:3000]:  # cap rows
                    rows.append([fpath, meta.get("url",""), it.get("idx"), it.get("clickable"), it.get("tag"), it.get("css"),
                                 (it.get("text") or "")[:140], it.get("aria"), it.get("title"), it.get("href"), it.get("role"),
                                 it.get("idAttr"), it.get("nameAttr"), it.get("type"), str(it.get("rect")),
                                 it.get("type", ""), it.get("selector", ""), it.get("class", "")])
                csv_buffer.extend(rows)
            except Exception:
                pass

            # Then descend into child frames
            frames = []
            try:
                frames = self._driver.find_elements("css selector", "iframe,frame")
            except Exception:
                frames = []
            for idx, fr in enumerate(frames):
                meta_fr = {"index": idx}
                try:
                    meta_fr["id"] = fr.get_attribute("id") or ""
                    meta_fr["name"] = fr.get_attribute("name") or ""
                    meta_fr["src"] = fr.get_attribute("src") or ""
                except Exception:
                    pass

                # Try switch
                try:
                    self._driver.switch_to.frame(fr)
                except Exception as e:
                    snap["frames"].append({"frame_chain": chain_prefix+[meta_fr], "unreachable": True, "error": str(e)})
                    continue

                recurse_frames(chain_prefix+[meta_fr])

                # pop back
                try:
                    self._driver.switch_to.parent_frame()
                except Exception:
                    try: self._driver.switch_to.default_content()
                    except Exception: pass

        # Run
        try:
            self._driver.switch_to.default_content()
        except Exception: pass

        csv_buffer = []
        recurse_frames([])

        # Save master JSON/CSV
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(snap, f, indent=2)
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["frame_path", "url", "idx", "clickable", "tag", "css", "text", "aria", "title", "href", "role", "id", "name", "type", "rect", "element_type", "selector", "class"])
                w.writerows(csv_buffer)
            self.enqueue(f"[INSPECT] DEEP snapshot saved:\n  JSON: {json_path}\n  CSV : {csv_path}\n  (+ per-frame HTML files)")
        except Exception as e:
            self.enqueue(f"[INSPECT][ERROR] {e}")

# ------------------------ Run ------------------------
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = App(root)
        root.mainloop()
    except Exception as e:
        print("[FATAL] GUI failed to start:", e)
