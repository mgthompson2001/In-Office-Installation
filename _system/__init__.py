"""
System Package - Auto-enable Browser Monitoring
This __init__.py ensures browser monitoring is enabled when _system is imported.
"""

import sys
from pathlib import Path

# Get installation directory
_current_file = Path(__file__).resolve()
installation_dir = _current_file.parent.parent

# Ensure _system is in path
system_dir = installation_dir / "_system"
if str(system_dir) not in sys.path:
    sys.path.insert(0, str(system_dir))

# Try to install monitoring bridge
try:
    from bot_launcher_bridge import install_monitoring_bridge
    install_monitoring_bridge()
except Exception:
    pass  # Silent fail - don't break anything

