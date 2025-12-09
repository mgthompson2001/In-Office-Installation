#!/usr/bin/env python3
"""
Browser Monitoring Diagnostics
Comprehensive diagnostic tool to identify why browser events aren't being captured.
"""

import sys
import sqlite3
import time
from pathlib import Path
from datetime import datetime
import traceback

# Get installation directory
_current_file = Path(__file__).resolve()
if "In-Office Installation" in str(_current_file):
    installation_dir = _current_file.parent.parent
else:
    installation_dir = Path.cwd()
    if "_bots" in str(installation_dir):
        installation_dir = installation_dir.parent

system_dir = installation_dir / "_system"
secure_data_dir = installation_dir / "_secure_data"

# Add system directory to path
if str(system_dir) not in sys.path:
    sys.path.insert(0, str(system_dir))

print("=" * 70)
print("Browser Monitoring Diagnostics")
print("=" * 70)
print()

# Test 1: Check if monitoring bridge is installed
print("[TEST 1] Checking monitoring bridge installation...")
try:
    from auto_webdriver_wrapper import install_auto_wrapper
    from browser_activity_monitor import get_browser_monitor
    
    # Check if wrapper is installed
    try:
        from selenium import webdriver
        is_wrapped = hasattr(webdriver.Chrome, '__new__') and 'AutoWrappedChrome' in str(webdriver.Chrome)
        print(f"  [OK] webdriver.Chrome is patched: {is_wrapped}")
        print(f"  [INFO] webdriver.Chrome class: {webdriver.Chrome}")
    except Exception as e:
        print(f"  [FAIL] Could not check webdriver.Chrome: {e}")
    
    # Check if monitor exists
    try:
        monitor = get_browser_monitor(installation_dir)
        print(f"  [OK] Browser monitor instance exists")
        print(f"  [INFO] Collection active: {monitor.collection_active}")
        print(f"  [INFO] Database path: {monitor.db_path}")
    except Exception as e:
        print(f"  [FAIL] Could not get browser monitor: {e}")
        traceback.print_exc()
    
except Exception as e:
    print(f"  [FAIL] Could not import monitoring modules: {e}")
    traceback.print_exc()

print()

# Test 2: Check database for recent activity
print("[TEST 2] Checking database for recent activity...")
try:
    db_path = secure_data_dir / "browser_activity.db"
    if not db_path.exists():
        print(f"  [FAIL] Database not found: {db_path}")
    else:
        print(f"  [OK] Database exists: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check session summaries
        cursor.execute("SELECT COUNT(*) FROM session_summaries")
        session_count = cursor.fetchone()[0]
        print(f"  [INFO] Total sessions: {session_count}")
        
        # Get most recent session
        cursor.execute("""
            SELECT session_id, bot_name, start_time, total_pages, total_actions 
            FROM session_summaries 
            ORDER BY start_time DESC 
            LIMIT 1
        """)
        recent_session = cursor.fetchone()
        if recent_session:
            print(f"  [INFO] Most recent session:")
            print(f"    - Session ID: {recent_session[0]}")
            print(f"    - Bot name: {recent_session[1]}")
            print(f"    - Start time: {recent_session[2]}")
            print(f"    - Total pages: {recent_session[3]}")
            print(f"    - Total actions: {recent_session[4]}")
        
        # Check page navigations
        cursor.execute("SELECT COUNT(*) FROM page_navigations")
        nav_count = cursor.fetchone()[0]
        print(f"  [INFO] Total page navigations: {nav_count}")
        
        # Check element interactions
        cursor.execute("SELECT COUNT(*) FROM element_interactions")
        element_count = cursor.fetchone()[0]
        print(f"  [INFO] Total element interactions: {element_count}")
        
        # Check form field interactions
        cursor.execute("SELECT COUNT(*) FROM form_field_interactions")
        form_count = cursor.fetchone()[0]
        print(f"  [INFO] Total form field interactions: {form_count}")
        
        # Check if events exist for recent session
        if recent_session:
            session_id = recent_session[0]
            cursor.execute("SELECT COUNT(*) FROM page_navigations WHERE session_id = ?", (session_id,))
            session_navs = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM element_interactions WHERE session_id = ?", (session_id,))
            session_elements = cursor.fetchone()[0]
            print(f"  [INFO] Events for recent session '{session_id}':")
            print(f"    - Page navigations: {session_navs}")
            print(f"    - Element interactions: {session_elements}")
        
        conn.close()
        
except Exception as e:
    print(f"  [FAIL] Database check failed: {e}")
    traceback.print_exc()

print()

# Test 3: Test EventFiringWebDriver wrapping
print("[TEST 3] Testing EventFiringWebDriver wrapping...")
try:
    # CRITICAL: Install monitoring bridge BEFORE importing selenium
    try:
        from fix_direct_launches import install_monitoring_bridge
        install_monitoring_bridge()
        print("  [OK] Monitoring bridge installed before selenium import")
    except Exception as e:
        print(f"  [WARN] Could not install monitoring bridge: {e}")
    
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.support.events import EventFiringWebDriver
    from webdriver_manager.chrome import ChromeDriverManager
    
    # Check if Chrome class is wrapped
    chrome_class = webdriver.Chrome
    print(f"  [INFO] webdriver.Chrome class: {chrome_class}")
    print(f"  [INFO] webdriver.Chrome module: {chrome_class.__module__}")
    print(f"  [INFO] webdriver.Chrome class name: {chrome_class.__name__}")
    print(f"  [INFO] webdriver.Chrome __qualname__: {getattr(chrome_class, '__qualname__', 'N/A')}")
    
    # Check if it's AutoWrappedChrome
    try:
        from auto_webdriver_wrapper import install_auto_wrapper
        # Get the actual class being used
        class_name = chrome_class.__name__
        qualname = getattr(chrome_class, '__qualname__', '')
        is_auto_wrapped = 'AutoWrappedChrome' in str(chrome_class) or 'AutoWrappedChrome' in qualname
        print(f"  [INFO] Is AutoWrappedChrome: {is_auto_wrapped}")
    except:
        pass
    
    # Try to create a test driver (headless)
    print("  [INFO] Creating test driver (headless)...")
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        service = ChromeService(ChromeDriverManager().install())
        test_driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Check if driver is wrapped
        is_event_firing = isinstance(test_driver, EventFiringWebDriver)
        print(f"  [INFO] Driver is EventFiringWebDriver: {is_event_firing}")
        print(f"  [INFO] Driver type: {type(test_driver)}")
        
        if is_event_firing:
            print(f"  [OK] Driver is properly wrapped with EventFiringWebDriver")
            # Check if listener is attached
            if hasattr(test_driver, '_listener'):
                listener = test_driver._listener
                print(f"  [OK] Event listener is attached")
                print(f"  [INFO] Listener type: {type(listener)}")
                print(f"  [INFO] Listener has monitor: {hasattr(listener, 'monitor')}")
                if hasattr(listener, 'monitor'):
                    print(f"  [INFO] Monitor collection active: {listener.monitor.collection_active}")
            else:
                print(f"  [WARN] Event listener not found in driver")
        else:
            print(f"  [FAIL] Driver is NOT wrapped with EventFiringWebDriver")
            print(f"  [INFO] This means events will NOT be captured!")
        
        # Test navigation
        print("  [INFO] Testing navigation to google.com...")
        test_driver.get("https://www.google.com")
        print(f"  [INFO] Navigation completed")
        print(f"  [INFO] Current URL: {test_driver.current_url}")
        print(f"  [INFO] Page title: {test_driver.title}")
        
        # Check if events were recorded
        time.sleep(2)  # Wait for events to be processed
        conn = sqlite3.connect(secure_data_dir / "browser_activity.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM page_navigations WHERE url LIKE '%google.com%' ORDER BY timestamp DESC LIMIT 1")
        recent_nav = cursor.fetchone()[0]
        if recent_nav > 0:
            print(f"  [OK] Navigation event was recorded!")
        else:
            print(f"  [FAIL] Navigation event was NOT recorded!")
        conn.close()
        
        # Cleanup
        test_driver.quit()
        print(f"  [OK] Test driver closed")
        
    except Exception as e:
        print(f"  [FAIL] Could not create test driver: {e}")
        traceback.print_exc()
    
except Exception as e:
    print(f"  [FAIL] EventFiringWebDriver test failed: {e}")
    traceback.print_exc()

print()

# Test 4: Check event listener implementation
print("[TEST 4] Checking event listener implementation...")
try:
    from browser_activity_monitor import BrowserActivityListener, BrowserActivityMonitor
    
    # Check if listener class exists
    print(f"  [OK] BrowserActivityListener class exists")
    print(f"  [INFO] Listener class: {BrowserActivityListener}")
    
    # Check if listener has required methods
    required_methods = ['before_navigate_to', 'after_navigate_to', 'after_click', 'after_change_value_of']
    for method in required_methods:
        if hasattr(BrowserActivityListener, method):
            print(f"  [OK] Listener has method: {method}")
        else:
            print(f"  [FAIL] Listener missing method: {method}")
    
    # Check if listener inherits from AbstractEventListener
    try:
        from selenium.webdriver.support.events import AbstractEventListener
        is_subclass = issubclass(BrowserActivityListener, AbstractEventListener)
        print(f"  [INFO] Listener inherits from AbstractEventListener: {is_subclass}")
    except:
        print(f"  [WARN] Could not check AbstractEventListener inheritance")
    
except Exception as e:
    print(f"  [FAIL] Event listener check failed: {e}")
    traceback.print_exc()

print()

# Test 5: Check monitoring bridge installation
print("[TEST 5] Checking monitoring bridge installation...")
try:
    from fix_direct_launches import install_monitoring_bridge
    
    # Check if bridge is installed
    bridge_installed = install_monitoring_bridge()
    print(f"  [INFO] Monitoring bridge installation result: {bridge_installed}")
    
    # Check if selenium is patched
    try:
        from selenium import webdriver
        # Check if webdriver.Chrome is patched
        chrome_code = webdriver.Chrome.__new__.__code__ if hasattr(webdriver.Chrome, '__new__') else None
        if chrome_code:
            print(f"  [OK] webdriver.Chrome has __new__ method (likely patched)")
        else:
            print(f"  [WARN] webdriver.Chrome does not have __new__ method")
    except Exception as e:
        print(f"  [FAIL] Could not check webdriver.Chrome: {e}")
    
except Exception as e:
    print(f"  [FAIL] Monitoring bridge check failed: {e}")
    traceback.print_exc()

print()

# Test 6: Check activity buffer
print("[TEST 6] Checking activity buffer...")
try:
    monitor = get_browser_monitor(installation_dir)
    buffer_size = len(monitor.activity_buffer)
    print(f"  [INFO] Activity buffer size: {buffer_size}")
    if buffer_size > 0:
        print(f"  [WARN] Activity buffer has {buffer_size} unprocessed records!")
        print(f"  [INFO] This means events are being recorded but not flushed to database")
    else:
        print(f"  [OK] Activity buffer is empty (all events processed)")
    
    # Check background processing thread
    if monitor.processing_thread and monitor.processing_thread.is_alive():
        print(f"  [OK] Background processing thread is running")
    else:
        print(f"  [WARN] Background processing thread is NOT running!")
        print(f"  [INFO] This means events may not be flushed to database")
    
except Exception as e:
    print(f"  [FAIL] Activity buffer check failed: {e}")
    traceback.print_exc()

print()

# Test 7: Check log file for errors
print("[TEST 7] Checking log file for errors...")
try:
    log_file = secure_data_dir / "browser_activity.log"
    if log_file.exists():
        print(f"  [OK] Log file exists: {log_file}")
        
        # Read last 20 lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            recent_lines = lines[-20:] if len(lines) > 20 else lines
            
            print(f"  [INFO] Last 20 log entries:")
            for line in recent_lines:
                if 'ERROR' in line or 'WARN' in line or 'FAIL' in line:
                    print(f"    [ALERT] {line.strip()}")
                elif 'Browser activity' in line or 'collection' in line.lower():
                    print(f"    [INFO] {line.strip()}")
    else:
        print(f"  [WARN] Log file not found: {log_file}")
        
except Exception as e:
    print(f"  [FAIL] Log file check failed: {e}")
    traceback.print_exc()

print()

# Summary
print("=" * 70)
print("DIAGNOSTIC SUMMARY")
print("=" * 70)
print()
print("Key Findings:")
print("1. If webdriver.Chrome is NOT wrapped: Events will NOT be captured")
print("2. If driver is NOT EventFiringWebDriver: Events will NOT be captured")
print("3. If activity buffer has records: Events are recorded but not flushed")
print("4. If background thread is NOT running: Events may not be flushed")
print("5. If listener methods are missing: Events will NOT be captured")
print()
print("Next Steps:")
print("- If driver is not wrapped: Check monitoring bridge installation")
print("- If events are buffered but not flushed: Check background processing thread")
print("- If listener methods are missing: Check event listener implementation")
print()
print("=" * 70)

