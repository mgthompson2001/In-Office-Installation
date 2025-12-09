"""
Bots Package - Auto-enable Browser Monitoring & System-Wide Passive Cleanup
This __init__.py ensures browser monitoring is enabled for all bots in this folder
AND runs passive cleanup system-wide (not just when Medisoft bot runs).
"""

import sys
import threading
from pathlib import Path

# Get installation directory
_current_file = Path(__file__).resolve()
installation_dir = _current_file.parent.parent

# Add _system to path
system_dir = installation_dir / "_system"
if str(system_dir) not in sys.path:
    sys.path.insert(0, str(system_dir))

# CRITICAL: Install monitoring bridge BEFORE selenium is imported
# This ensures webdriver.Chrome is patched before any bot uses it
try:
    from bot_launcher_bridge import install_monitoring_bridge
    # Install immediately (before any selenium imports)
# DATA COLLECTION DISABLED
#     install_monitoring_bridge()
except Exception:
    pass  # Silent fail - don't break any bots

# ============================================================================
# SYSTEM-WIDE PASSIVE CLEANUP - Runs automatically for ALL bots
# ============================================================================
# This ensures cleanup runs regardless of which bot is used
# No bot code needs to be modified - this runs at import time

def _init_system_cleanup():
    """Initialize system-wide passive cleanup in background thread."""
    try:
        # Import cleanup helper
        cleanup_helper_path = installation_dir / "_bots" / "Billing Department" / "init_passive_cleanup.py"
        if cleanup_helper_path.exists():
            # Add to path if needed
            bots_dir = installation_dir / "_bots"
            if str(bots_dir) not in sys.path:
                sys.path.insert(0, str(bots_dir))
            
            # Import and run cleanup
            from init_passive_cleanup import init_passive_cleanup
            # Run in background thread (non-blocking)
            cleanup_thread = threading.Thread(
                target=init_passive_cleanup,
                args=(installation_dir, None),
                daemon=True,
                name="SystemCleanup"
            )
            cleanup_thread.start()
    except Exception:
        # Silent fail - don't break any bots if cleanup fails
        pass

# Run cleanup automatically when any bot imports this package
_init_system_cleanup()

# Also patch selenium at module level if it hasn't been imported yet
if 'selenium' not in sys.modules:
    # Create import hook to patch selenium when it's imported
    original_import = __builtins__.__import__
    
    def patched_import(name, *args, **kwargs):
        module = original_import(name, *args, **kwargs)
        
        # If selenium.webdriver is being imported, ensure wrapper is installed
        if name == 'selenium' or name.startswith('selenium.'):
            try:
                from bot_launcher_bridge import install_monitoring_bridge
# DATA COLLECTION DISABLED
#                 install_monitoring_bridge()
            except:
                pass
        
        return module
    
    # Note: We can't safely patch __builtins__.__import__ globally
    # Instead, rely on the fact that install_monitoring_bridge() patches webdriver.Chrome
    # This happens when the module is imported, which should be before selenium is used
