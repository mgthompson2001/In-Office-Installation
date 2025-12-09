#!/usr/bin/env python3
"""
Auto-Enable Browser Monitoring
DISABLED: Data collection has been turned off.
Import this module at the top of any bot to automatically enable browser activity monitoring.
"""

# DATA COLLECTION DISABLED
ENABLE_MONITORING = False

import sys
from pathlib import Path

# Get installation directory
_current_file = Path(__file__)
if _current_file.name == "auto_enable_browser_monitoring.py":
    installation_dir = _current_file.parent.parent
else:
    installation_dir = Path(__file__).parent.parent

# Monitoring is disabled - do nothing
# All monitoring code has been disabled