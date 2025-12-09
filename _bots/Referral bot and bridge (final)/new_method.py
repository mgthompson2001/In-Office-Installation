    def fill_service_file_fields_and_save_final(self, row_value: str, timeout: int = 25) -> bool:
        """
        Robust final attempt to:
          - set Billing Note to "IA Only"
          - set New/Reassignment (n/r + Enter or JS fallback)
          - click Save (iframeEditSaveButton)
        This aggressively:
          - switches into dynamic iframe(s),
          - clicks every tab to load panes,
          - tries many heuristics to find the billing field (label-following, name/id patterns, generic visible input),
          - uses JS recursive write fallback and keyboard fallback,
          - verifies readback and logs detailed debug about every attempt.
        Returns True on success, False otherwise. Logs extensively.
        """
        if not self.driver:
            self.log("[SERVICE-FILE-FINAL] No webdriver.")
            return False

        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time, traceback, re

        d = self.driver
        wait = WebDriverWait(d, timeout)

        billing_text_variants = ["Billing Note", "Billing Notes", "Billing", "Billing note", "Billing notes", "Billing Note:"]
        billing_name_patterns = ["progprovexp", "cm", "pi", "billing", "provexp"]
        newor_name = "FLD_ctprogprovexp_progprovexp3"  # fallback name guessed earlier
        save_button_id = "iframeEditSaveButton"

        rv = (row_value or "").strip().lower()
        key_letter = "n" if "new" in rv else ("r" if "reassign" in rv or "re-assignment" in rv else "n")
        js_select_value = "2" if key_letter == "n" else "3"

        def log_exc(tag, e):
            self.log(f"[SERVICE-FILE-FINAL][{tag}] {e}")
            try:
                self.log(traceback.format_exc())
            except Exception:
                pass

        def click_all_tabs_if_present():
            """
            Find likely tab headers in the current iframe/document and click them in order.
            Returns list of (index, text) clicked.
            """
            clicked = []
            try:
                # candidate XPath patterns for tab headers
                tab_xpaths = [
                    "//ul[contains(@class,'wizTabs')]/li/a",
                    "//ul[contains(@class,'tabs')]/li/a",
                    "//div[contains(@class,'tabstrip')]//a",
                    "//a[contains(@class,'ui-tabs-anchor')]",
                    "//li[contains(@class,'wizTab') or contains(@class,'tab')]/a",
                    "//div[@role='tab']",
                    "//a[contains(@id,'tab') or contains(@class,'tab')]"
                ]
                tabs = []
                for xp in tab_xpaths:
                    try:
                        els = d.find_elements(By.XPATH, xp)
                        if els:
                            for e in els:
                                # avoid duplicates
                                if e not in tabs:
                                    tabs.append(e)
                    except Exception:
                        continue

                # If no anchors found, try BUTTONS or headings that toggle panes
                if not tabs:
                    try:
                        btns = d.find_elements(By.XPATH, "//button[contains(@class,'tab') or contains(@id,'tab')]")
                        for b in btns:
                            if b not in tabs:
                                tabs.append(b)
                    except Exception:
                        pass

                # Click each visible tab (with small pause to let pane render)
                for i, t in enumerate(tabs):
                    try:
                        if not t.is_displayed():
                            continue
                        try:
                            txt = t.text.strip()
                        except Exception:
                            txt = "<no-text>"
                        try:
                            d.execute_script("arguments[0].scrollIntoView({block:'center'});", t)
                        except Exception:
                            pass
                        try:
                            t.click()
                        except Exception:
                            try:
                                d.execute_script("arguments[0].click();", t)
                            except Exception:
                                continue
                        time.sleep(0.30)
                        clicked.append((i, txt))
                    except Exception as e:
                        log_exc("TABCLICK", e)
                        continue
            except Exception as e:
                log_exc("TABS", e)
            return clicked

        def find_billing_by_label_following():
            """
            Look for TD/TH labels matching billing variants and get following sibling input/textarea/select.
            """
            for text_variant in billing_text_variants:
                try:
                    # find td or th having label text
                    xp = f"//td[normalize-space()='{text_variant}'] | //th[normalize-space()='{text_variant}'] | //label[normalize-space()='{text_variant}']"
                    labels = d.find_elements(By.XPATH, xp)
                    for lab in labels:
                        try:
                            # try sibling input/textarea/select
                            try:
                                sib = lab.find_element(By.XPATH, "following-sibling::td//input | following-sibling::td//textarea | following-sibling::td//select")
                                return sib, f"label_following:{text_variant}"
                            except Exception:
                                pass
                            # if label is parent of control
                            try:
                                ctr = lab.find_element(By.XPATH, ".//input | .//textarea | .//select")
                                return ctr, f"label_nested:{text_variant}"
                            except Exception:
                                pass
                        except Exception:
                            continue
                except Exception:
                    continue
            return None, None

        def find_billing_by_name_pattern():
            """
            Find inputs/textarea whose name/id contains any of the billing_name_patterns
            """
            for pat in billing_name_patterns:
                try:
                    # input or textarea
                    els = d.find_elements(By.XPATH, f"//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{pat}') or contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{pat}')] | //textarea[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{pat}') or contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{pat}')]")
                    if els:
                        # prefer visible
                        for e in els:
                            try:
                                if e.is_displayed():
                                    return e, f"namepattern:{pat}"
                            except Exception:
                                return els[0], f"namepattern:{pat}"
                except Exception:
                    continue
            return None, None

        def find_first_visible_editable():
            """
            Return first visible input/textarea/select in the current document (conservative).
            """
            try:
                els = d.find_elements(By.XPATH, "//textarea | //input[not(@type='hidden') and not(@disabled)] | //select")
                for e in els:
                    try:
                        if e.is_displayed():
                            return e, "first_visible_editable"
                    except Exception:
                        continue
            except Exception:
                pass
            return None, None

        def js_recursive_find_and_set(name_matchers, value):
            """
            Execute JS to find an element whose name/id/text matches the name_matchers (list of strings),
            set its value and dispatch change. Returns dict result from JS.
            """
            try:
                # the JS tries to find inputs/textarea/select whose name/id includes one of the matchers OR label text includes
                js = r"""
                var matchers = arguments[0]; var val = arguments[1];
                function checkDoc(doc) {
                    try {
                        var inputs = [].slice.call(doc.querySelectorAll('input, textarea, select'));
                        for(var i=0;i<inputs.length;i++){
                            var el = inputs[i];
                            var nm = (el.getAttribute('name')||'').toLowerCase();
                            var id = (el.getAttribute('id')||'').toLowerCase();
                            var txt = (el.innerText||'').toLowerCase();
                            for(var j=0;j<matchers.length;j++){
                                var m = matchers[j].toLowerCase();
                                if((nm && nm.indexOf(m) !== -1) || (id && id.indexOf(m) !== -1) || (txt && txt.indexOf(m)!==-1)){
                                    try { if(el.tagName.toLowerCase()==='select') el.value = val; else el.value = val; } catch(e){}
                                    try { el.dispatchEvent(new Event('change',{bubbles:true})); } catch(e){}
                                    return {ok:true, where: (doc.location?doc.location.href:'doc'), tag: el.tagName, name: nm, id:id};
                                }
                            }
                        }
                    } catch(e){}
                    // recurse into iframes one level
                    var frames = doc.getElementsByTagName('iframe');
                    for(var k=0;k<frames.length;k++){
                        try{
                            var frdoc = frames[k].contentDocument || frames[k].contentWindow.document;
                            if(!frdoc) continue;
                            var r = checkDoc(frdoc);
                            if(r && r.ok){ r.frameIndex = k; return r;}
                        }catch(e){}
                    }
                    return {ok:false};
                }
                try { return checkDoc(document); } catch(e) { return {ok:false, err:String(e)}; }
                """
                res = d.execute_script(js, name_matchers, value)
                return res
            except Exception as e:
                log_exc("JSRECURSIVE", e)
                return {"ok": False, "err": str(e)}

        def set_value_on_element(el, value):
            """
            Try using regular element methods then JS fallback to set value and dispatch change.
            Returns True on verified success.
            """
            try:
                try:
                    d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                except Exception:
                    pass
                try:
                    el.click()
                except Exception:
                    pass
                try:
                    el.clear()
                except Exception:
                    try:
                        d.execute_script("arguments[0].value='';", el)
                    except Exception:
                        pass
                # Try send_keys
                try:
                    el.send_keys(value)
                    try:
                        d.execute_script("arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
                    except Exception:
                        pass
                except Exception:
                    # JS fallback on the element
                    try:
                        d.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el, value)
                    except Exception as e:
                        log_exc("SETVAL-EL-JS", e)
                        return False
                # readback verification
                try:
                    val = el.get_attribute("value")
                except Exception:
                    try:
                        val = d.execute_script("return arguments[0].value;", el)
                    except Exception:
                        val = None
                if val and value in val:
                    return True
                # As last resort, try reading document.getElementsByName
                try:
                    nm = el.get_attribute("name")
                    if nm:
                        try:
                            v2 = d.execute_script("var e=document.getElementsByName(arguments[0])[0]; return e?e.value:null;", nm)
                            if v2 and value in v2:
                                return True
                        except Exception:
                            pass
                except Exception:
                    pass
                return False
            except Exception as e:
                log_exc("SETVAL-EL", e)
                return False

        # --------- Start main flow ----------
        try:
            # ensure top-level context first
            try:
                d.switch_to.default_content()
            except Exception:
                pass

            # wait shortly for editLayer (not fatal)
            try:
                WebDriverWait(d, 5).until(lambda drv: bool(drv.find_elements(By.ID, "editLayer")))
                self.log("[SERVICE-FILE-FINAL] editLayer present.")
            except Exception:
                self.log("[SERVICE-FILE-FINAL] editLayer did not appear quickly; continuing to frame scan.")

            # switch into the dynamic iframe (preferred)
            switched = False
            for fid in ("dynamicIframe", "dynamicAltframe", "iframeWrapper", "iframeEdit"):
                try:
                    try:
                        WebDriverWait(d, 3).until(EC.frame_to_be_available_and_switch_to_it((By.ID, fid)))
                        self.log(f"[SERVICE-FILE-FINAL] Switched into iframe '{fid}'.")
                        switched = True
                        break
                    except Exception:
                        # fallback by name
                        try:
                            d.switch_to.default_content()
                            d.switch_to.frame(fid)
                            self.log(f"[SERVICE-FILE-FINAL] Switched into frame by name '{fid}'.")
                            switched = True
                            break
                        except Exception:
                            d.switch_to.default_content()
                            continue
                except Exception:
                    continue

            if not switched:
                self.log("[SERVICE-FILE-FINAL] Could not find a known dynamic iframe directly; scanning top-level frames instead.")
            time.sleep(0.25)

            # Click every tab so its pane DOM is loaded/rendered
            tabs_clicked = click_all_tabs_if_present()
            self.log(f"[SERVICE-FILE-FINAL] Tabs clicked: {tabs_clicked}")

            # Attempt strategies in the current frame/document and each pane we've activated
            billing_written = False
            found_by = None
            found_element = None

            # Strategy A: label-following in current doc
            try:
                el, reason = find_billing_by_label_following()
                if el:
                    self.log(f"[SERVICE-FILE-FINAL] Found billing field by label-following ({reason}).")
                    if set_value_on_element(el, "IA Only"):
                        billing_written = True
                        found_by = reason
                        found_element = el
                    else:
                        self.log("[SERVICE-FILE-FINAL] Setting billing via element failed for label-following.")
            except Exception as e:
                log_exc("LABEL-FOLLOW", e)

            # Strategy B: name/id pattern
            if not billing_written:
                try:
                    el, reason = find_billing_by_name_pattern()
                    if el:
                        self.log(f"[SERVICE-FILE-FINAL] Found billing field by name pattern ({reason}).")
                        if set_value_on_element(el, "IA Only"):
                            billing_written = True
                            found_by = reason
                            found_element = el
                        else:
                            self.log("[SERVICE-FILE-FINAL] Setting billing via element failed for name pattern.")
                except Exception as e:
                    log_exc("NAME-PATTERN", e)

            # Strategy C: first visible editable
            if not billing_written:
                try:
                    el, reason = find_first_visible_editable()
                    if el:
                        self.log(f"[SERVICE-FILE-FINAL] Found first visible editable ({reason}). Attempting to set.")
                        if set_value_on_element(el, "IA Only"):
                            billing_written = True
                            found_by = reason
                            found_element = el
                        else:
                            self.log("[SERVICE-FILE-FINAL] Setting billing via element failed for first visible.")
                except Exception as e:
                    log_exc("FIRST-VISIBLE", e)

            # Strategy D: JS recursive search & set across current doc + nested frames
            if not billing_written:
                try:
                    res = js_recursive_find_and_set(billing_name_patterns + billing_text_variants, "IA Only")
                    self.log(f"[SERVICE-FILE-FINAL] JS recursive attempt result: {res}")
                    if isinstance(res, dict) and res.get("ok"):
                        billing_written = True
                        found_by = f"js_recursive:{res.get('where','unknown')}"
                    else:
                        billing_written = False
                except Exception as e:
                    log_exc("JS-RECUR", e)
                    billing_written = False

            # Strategy E: Keyboard/tab fallback (only if necessary)
            if not billing_written:
                try:
                    self.log("[SERVICE-FILE-FINAL] Trying keyboard/tab fallback (fragile) to focus inputs.")
                    # attempt a limited tab-through in current frame
                    for _ in range(2):  # two passes: inner frames may be re-exposed
                        try:
                            # attempt to gather focusable elements and iterate
                            focusables = d.find_elements(By.CSS_SELECTOR, "input,textarea,select,button,a")
                            for f_idx, fe in enumerate(focusables):
                                try:
                                    if not fe.is_displayed():
                                        continue
                                    try:
                                        fe.click()
                                    except Exception:
                                        try:
                                            d.execute_script("arguments[0].focus();", fe)
                                        except Exception:
                                            pass
                                    # check if this matches billing by name/id
                                    nm = ""
                                    try:
                                        nm = (fe.get_attribute("name") or "") + "|" + (fe.get_attribute("id") or "")
                                    except Exception:
                                        nm = ""
                                    if any(pat in nm.lower() for pat in billing_name_patterns):
                                        if set_value_on_element(fe, "IA Only"):
                                            billing_written = True
                                            found_by = f"keyboard_focus:{nm}"
                                            found_element = fe
                                            break
                                except Exception:
                                    continue
                            if billing_written:
                                break
                        except Exception:
                            pass
                except Exception as e:
                    log_exc("KB-FALLBACK", e)

            # Final billing check
            if not billing_written:
                self.log("[SERVICE-FILE-FINAL][ERROR] Billing Note could NOT be written after ALL strategies.")
                # dump helpful context
                try:
                    # top-level frames
                    frames = d.find_elements(By.TAG_NAME, "iframe")
                    self.log(f"[SERVICE-FILE-FINAL] top-level frames count: {len(frames)}")
                    for i, fr in enumerate(frames):
                        try:
                            self.log(f"[SERVICE-FILE-FINAL] frame[{i}] id='{fr.get_attribute('id')}', name='{fr.get_attribute('name')}', src='{fr.get_attribute('src')}', displayed={fr.is_displayed()}")
                        except Exception:
                            continue
                except Exception:
                    pass
                return False

            self.log(f"[SERVICE-FILE-FINAL] Billing Note set successfully by: {found_by}")

            # ------------------ Set New/Reassignment ------------------
            select_set = False
            try:
                # try to find select by name (best)
                try:
                    sel = d.find_element(By.NAME, newor_name)
                    try:
                        sel.click()
                    except Exception:
                        pass
                    sel.send_keys(key_letter)
                    time.sleep(0.08)
                    sel.send_keys(Keys.ENTER)
                    self.log(f"[SERVICE-FILE-FINAL] Sent '{key_letter}'+ENTER to select by name '{newor_name}'.")
                    select_set = True
                except Exception:
                    # try common fallbacks for selects
                    try:
                        sel = d.find_element(By.XPATH, "//select[contains(@name,'progprovexp') or contains(@id,'progprovexp') or contains(@name,'new') or contains(@id,'new')]")
                        sel.click()
                        sel.send_keys(key_letter)
                        time.sleep(0.06)
                        sel.send_keys(Keys.ENTER)
                        select_set = True
                        self.log("[SERVICE-FILE-FINAL] Sent letter+enter to fallback select.")
                    except Exception:
                        pass

                if not select_set:
                    # JS recursive set for select value
                    js_setselect = r"""
                    var name = arguments[0], val = arguments[1];
                    function trySet(d){
                        try{
                            var s = d.getElementsByName(name);
                            if(s && s.length>0){ s[0].value = val; try{s[0].dispatchEvent(new Event('change',{bubbles:true}));}catch(e){}; return {ok:true};}
                        }catch(e){}
                        var frames = d.getElementsByTagName('iframe');
                        for(var i=0;i<frames.length;i++){
                            try{
                                var sub = frames[i].contentDocument || frames[i].contentWindow.document;
                                if(!sub) continue;
                                var r = trySet(sub);
                                if(r && r.ok){ r.index = i; return r; }
                            }catch(e){}
                        }
                        return {ok:false};
                    }
                    try { return trySet(document); } catch(e) { return {ok:false,err:String(e)}; }
                    """
                    res = d.execute_script(js_setselect, newor_name, js_select_value)
                    self.log(f"[SERVICE-FILE-FINAL] JS set select result: {res}")
                    if isinstance(res, dict) and res.get("ok"):
                        select_set = True
            except Exception as e:
                log_exc("SELECT-SET", e)

            if not select_set:
                self.log("[SERVICE-FILE-FINAL][WARN] Could not robustly set New/Reassignment; will attempt Save anyway.")

            # ------------------ Click Save ------------------
            try:
                d.switch_to.default_content()
            except Exception:
                pass
            time.sleep(0.25)
            try:
                savebtn = None
                try:
                    savebtn = wait.until(EC.element_to_be_clickable((By.ID, save_button_id)))
                except Exception:
                    try:
                        cands = d.find_elements(By.XPATH, "//li[@id='iframeEditSaveButton' or normalize-space()='save' or translate(normalize-space(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='save']")
                        savebtn = next((c for c in cands if c.is_displayed()), None)
                    except Exception:
                        savebtn = None

                if savebtn:
                    try:
                        savebtn.click()
                        self.log("[SERVICE-FILE-FINAL] Clicked Save button (Selenium).")
                        time.sleep(1.0)
                        return True
                    except Exception:
                        try:
                            d.execute_script("arguments[0].click();", savebtn)
                            self.log("[SERVICE-FILE-FINAL] Clicked Save via JS fallback.")
                            time.sleep(1.0)
                            return True
                        except Exception as e:
                            log_exc("SAVE-CLICK", e)
                            return False
                else:
                    # final JS click
                    try:
                        d.execute_script("var b=document.getElementById('iframeEditSaveButton'); if(b){ b.click(); }")
                        self.log("[SERVICE-FILE-FINAL] Final JS save-click attempted.")
                        time.sleep(1.0)
                        return True
                    except Exception as e:
                        log_exc("SAVE-FINAL", e)
                        return False

        except Exception as e:
            log_exc("MAIN", e)
            try:
                d.switch_to.default_content()
            except Exception:
                pass
            return False
