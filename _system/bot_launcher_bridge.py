#!/usr/bin/env python3
"""
Bot Launcher Bridge - Universal Browser Monitoring
Universal bridge that automatically monitors ALL bots in _bots folder.
Works for bots launched directly OR through Automation Hub.
"""

import sys
import os
from pathlib import Path

# Get installation directory
_current_file = Path(__file__).resolve()
if "In-Office Installation" in str(_current_file):
    installation_dir = _current_file.parent.parent
else:
    # Try to find from current working directory
    cwd = Path.cwd()
    if "In-Office Installation" in str(cwd):
        installation_dir = cwd.parent if cwd.name == "_bots" else cwd
    else:
        installation_dir = _current_file.parent.parent

# Ensure _system is in path
system_dir = installation_dir / "_system"
if str(system_dir) not in sys.path:
    sys.path.insert(0, str(system_dir))

# Install wrapper BEFORE any selenium imports
_installed = False

def install_monitoring_bridge():
    """Install universal browser monitoring bridge"""
    global _installed
    
    if _installed:
        return True
    
    try:
        from auto_webdriver_wrapper import install_auto_wrapper
        from browser_activity_monitor import get_browser_monitor
        
        # Install wrapper (patches webdriver.Chrome)
        success = install_auto_wrapper(installation_dir)
        
        if success:
            # Initialize browser monitor
            try:
                monitor = get_browser_monitor(installation_dir)
                if monitor:
                    monitor.start_collection()
                _installed = True
                return True
            except Exception:
                pass
        
        return False
    except Exception:
        return False

# Auto-install on import
install_monitoring_bridge()

# Also patch selenium at module level if it hasn't been imported yet
if 'selenium' not in sys.modules:
    # Create a hook to patch selenium when it's imported
    original_import = __builtins__.__import__
    
    def patched_import(name, *args, **kwargs):
        module = original_import(name, *args, **kwargs)
        
        # If selenium.webdriver is being imported, ensure wrapper is installed
        if name == 'selenium.webdriver' or (name == 'selenium' and 'webdriver' in str(args)):
            install_monitoring_bridge()
        
        return module
    
    # Note: Actually patching __builtins__.__import__ is dangerous and can break things
    # Instead, we'll rely on the wrapper being installed before selenium is used

