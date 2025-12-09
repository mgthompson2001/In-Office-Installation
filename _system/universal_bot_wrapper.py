#!/usr/bin/env python3
"""
Universal Bot Wrapper - Automatic Browser Monitoring Bridge
This module patches Selenium at the Python level to automatically monitor ALL bots.
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
    # Try to find installation directory from current working directory
    cwd = Path.cwd()
    if "In-Office Installation" in str(cwd):
        installation_dir = cwd.parent if cwd.name == "_bots" else cwd
    else:
        # Default: assume _system is in parent
        installation_dir = _current_file.parent.parent

# Install wrapper when module is imported
_installed = False

def install_universal_monitoring():
    """Install universal browser monitoring for all bots"""
    global _installed
    
    if _installed:
        return True
    
    try:
        # Add _system to path
        system_dir = installation_dir / "_system"
        if str(system_dir) not in sys.path:
            sys.path.insert(0, str(system_dir))
        
        # Install automatic wrapper
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
install_universal_monitoring()

