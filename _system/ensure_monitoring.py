#!/usr/bin/env python3
"""
Ensure Monitoring - Auto-install for all bots
This module can be imported at the start of any bot to ensure monitoring is active.
Safe to import - doesn't break anything if monitoring unavailable.
"""

import sys
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

# Add _system to path
if str(system_dir) not in sys.path:
    sys.path.insert(0, str(system_dir))

# Install monitoring bridge (silent fail if unavailable)
try:
    from fix_direct_launches import install_monitoring_bridge
    install_monitoring_bridge()
except:
    try:
        from bot_launcher_bridge import install_monitoring_bridge
        install_monitoring_bridge()
    except:
        pass  # Silent fail - bot still works

