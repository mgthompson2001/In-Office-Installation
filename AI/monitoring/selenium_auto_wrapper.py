#!/usr/bin/env python3
"""
Selenium Auto Wrapper - Automatic Browser Activity Monitoring
Monkey-patches Selenium WebDriver to automatically monitor browser activity.
Zero bot modifications needed - works transparently.
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


def _wrap_chrome_init(original_init, installation_dir: Optional[Path] = None):
    """Wrapper for Chrome WebDriver __init__"""
    def wrapped_init(self, *args, **kwargs):
        # Call original __init__
        original_init(self, *args, **kwargs)
        
        # Wrap with monitoring if available - but never crash if it fails
        if MONITOR_AVAILABLE and wrap_webdriver_for_monitoring:
            try:
                bot_name = _get_bot_name_from_stack()
                session_id = _generate_session_id()
                
                wrapped = wrap_webdriver_for_monitoring(
                    self,
                    session_id=session_id,
                    bot_name=bot_name,
                    installation_dir=installation_dir
                )
                
                # If wrapping created new driver, copy attributes
                if wrapped != self:
                    for attr in dir(wrapped):
                        if not attr.startswith('_') and not callable(getattr(wrapped, attr, None)):
                            try:
                                setattr(self, attr, getattr(wrapped, attr))
                            except:
                                pass
            except Exception as e:
                # Silently fail - bots must work even if monitoring is broken
                import logging
                logging.debug(f"Monitoring wrapper failed (non-critical): {e}")
                # Continue with original driver - bot functionality is unaffected
    
    return wrapped_init


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
        # Store original Chrome class
        original_chrome = webdriver.Chrome.__init__
        
        # Wrap Chrome __init__
        webdriver.Chrome.__init__ = _wrap_chrome_init(original_chrome, installation_dir)
        
        return True
    except Exception as e:
        print(f"Warning: Could not install auto WebDriver wrapper: {e}")
        return False


def uninstall_auto_wrapper():
    """Uninstall automatic WebDriver wrapper"""
    # Note: In practice, we'd restore the original, but for simplicity,
    # we'll just mark it as unwrapped
    pass

