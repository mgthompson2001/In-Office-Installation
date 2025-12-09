#!/usr/bin/env python3
"""
Auto-Enable Monitoring for Direct Launches
DISABLED: Data collection has been turned off.
Add this import at the TOP of any bot to ensure browser monitoring works.
"""

# DATA COLLECTION DISABLED
ENABLE_MONITORING = False

import sys
from pathlib import Path

# Get installation directory
_current_file = Path(__file__).resolve()
installation_dir = _current_file.parent.parent

# Add _system to path
system_dir = installation_dir / "_system"
if str(system_dir) not in sys.path:
    sys.path.insert(0, str(system_dir))

# Monitoring is disabled - do nothing
# All monitoring code has been disabled