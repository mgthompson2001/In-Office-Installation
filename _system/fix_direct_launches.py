#!/usr/bin/env python3
"""
Fix Direct Launches - Universal Browser Monitoring
DISABLED: Data collection has been turned off.
This module ensures browser monitoring works for bots launched directly (not through Automation Hub).
"""

# DATA COLLECTION DISABLED
ENABLE_MONITORING = False

import sys
import os
from pathlib import Path

# Get installation directory
_current_file = Path(__file__).resolve()
if "In-Office Installation" in str(_current_file):
    installation_dir = _current_file.parent.parent
else:
    installation_dir = Path.cwd()
    if "_bots" in str(installation_dir):
        installation_dir = installation_dir.parent

system_dir = installation_dir / "_system"

# Ensure _system is in path
if str(system_dir) not in sys.path:
    sys.path.insert(0, str(system_dir))

# Install monitoring bridge - DISABLED
_installed = False

def install_monitoring_bridge():
    """Install monitoring bridge - DISABLED"""
    # Monitoring is disabled - do nothing
    return False

# Do not install monitoring bridge
# install_monitoring_bridge()

# Hook into Python's import system - DISABLED
# All monitoring hooks are disabled