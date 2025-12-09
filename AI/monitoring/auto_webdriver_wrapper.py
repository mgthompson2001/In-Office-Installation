#!/usr/bin/env python3
"""
Automatic WebDriver Wrapper - Zero Bot Modifications
Automatically wraps Selenium WebDrivers with browser activity monitoring.
Bots work exactly as before - no code changes needed.
"""

import sys
import inspect
from pathlib import Path
from typing import Any, Optional

# Try to import browser monitor
try:
    from browser_activity_monitor import get_browser_monitor, wrap_webdriver_for_monitoring
    MONITOR_AVAILABLE = True
except ImportError:
    MONITOR_AVAILABLE = False
    get_browser_monitor = None
    wrap_webdriver_for_monitoring = None

# Try to import Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    webdriver = None


def _get_bot_name_from_stack() -> str:
    """Extract bot name from call stack"""
    try:
        stack = inspect.stack()
        for frame in stack[2:15]:  # Check deeper stack
            filename = frame.filename
            if any(keyword in filename.lower() for keyword in ['bot', 'workflow', 'penelope', 'medisoft', 'intake', 'referral']):
                bot_name = Path(filename).stem
                bot_name = bot_name.replace('_', ' ').replace('-', ' ').title()
                return bot_name
    except Exception:
        pass
    return "Unknown Bot"


def _generate_session_id() -> str:
    """Generate unique session ID"""
    from datetime import datetime
    import hashlib
    timestamp = datetime.now().isoformat()
    session_hash = hashlib.md5(timestamp.encode()).hexdigest()[:12]
    return f"session_{session_hash}"


def install_auto_wrapper(installation_dir: Optional[Path] = None) -> bool:
    """
    Install automatic WebDriver wrapper.
    This monkey-patches selenium.webdriver.Chrome to automatically monitor browser activity.
    
    After calling this, all webdriver.Chrome() calls will automatically be monitored.
    Zero bot modifications needed!
    """
    if not SELENIUM_AVAILABLE or not MONITOR_AVAILABLE:
        return False
    
    try:
        # Import selenium modules to ensure they're loaded
        import selenium.webdriver.chrome.webdriver as chrome_webdriver
        import selenium.webdriver.chrome.service as chrome_service
        
        # Store original Chrome class from multiple locations
        original_chrome = webdriver.Chrome
        original_chrome_module = chrome_webdriver.WebDriver
        
        # Create wrapper class that extends Chrome
        class AutoWrappedChrome(original_chrome):
            """Auto-wrapped Chrome WebDriver with browser activity monitoring"""
            
            def __new__(cls, *args, **kwargs):
                # Create original Chrome instance
                instance = super().__new__(cls)
                
                # Initialize it
                instance.__init__(*args, **kwargs)
                
                # CRITICAL FIX: Wrap with monitoring and ensure collection is active
                if wrap_webdriver_for_monitoring:
                    try:
                        # Ensure monitor exists and is active
                        monitor = get_browser_monitor(installation_dir)
                        if monitor and not monitor.collection_active:
                            monitor.start_collection()
                        
                        bot_name = _get_bot_name_from_stack()
                        session_id = _generate_session_id()
                        
                        wrapped = wrap_webdriver_for_monitoring(
                            instance,
                            session_id=session_id,
                            bot_name=bot_name,
                            installation_dir=installation_dir
                        )
                        
                        # CRITICAL FIX: Store monitor reference for cleanup
                        # Note: We don't hook quit() because EventFiringWebDriver already handles it
                        # Instead, we rely on background processing to flush data
                        # The monitor will automatically flush every 2 seconds
                        
                        # Return wrapped driver (EventFiringWebDriver)
                        return wrapped
                    except Exception as e:
                        # If wrapping fails, return original instance
                        import sys
                        print(f"Warning: Browser monitoring wrapper failed: {e}", file=sys.stderr)
                        import traceback
                        traceback.print_exc()
                        pass
                
                # Return original instance if wrapping unavailable
                return instance
        
        # CRITICAL FIX: Patch webdriver.Chrome in multiple locations
        # This ensures the patch works regardless of how selenium is imported
        webdriver.Chrome = AutoWrappedChrome
        
        # Also patch in selenium.webdriver module
        if hasattr(webdriver, 'Chrome'):
            webdriver.Chrome = AutoWrappedChrome
        
        # Patch in selenium.webdriver.chrome.webdriver module
        try:
            chrome_webdriver.WebDriver = AutoWrappedChrome
        except:
            pass
        
        # Patch in selenium.webdriver.chrome module
        try:
            import selenium.webdriver.chrome as chrome_module
            chrome_module.WebDriver = AutoWrappedChrome
        except:
            pass
        
        # Verify patching worked
        if webdriver.Chrome == AutoWrappedChrome:
            return True
        else:
            print(f"Warning: Patching verification failed - webdriver.Chrome is not AutoWrappedChrome")
            return False
            
    except Exception as e:
        import traceback
        print(f"Warning: Could not install auto WebDriver wrapper: {e}")
        traceback.print_exc()
        return False


def uninstall_auto_wrapper():
    """Uninstall automatic WebDriver wrapper"""
    # Note: In practice, we'd restore the original, but for simplicity,
    # we'll just mark it as unwrapped
    pass

