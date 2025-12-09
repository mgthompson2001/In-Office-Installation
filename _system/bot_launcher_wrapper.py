#!/usr/bin/env python3
"""
Bot Launcher Wrapper - Ensures Browser Monitoring Works
This wrapper script ensures monitoring is installed before running the bot.
Used by secure_launcher to guarantee monitoring works for all bots.
"""

import sys
import os
from pathlib import Path

# Get installation directory
if len(sys.argv) < 2:
    print("Usage: bot_launcher_wrapper.py <bot_script.py>")
    sys.exit(1)

bot_path = Path(sys.argv[1])

# Get installation directory
if "In-Office Installation" in str(bot_path):
    # Find the installation directory
    parts = bot_path.parts
    install_idx = None
    for i, part in enumerate(parts):
        if "In-Office Installation" in part:
            install_idx = i
            break
    
    if install_idx is not None:
        installation_dir = Path(*parts[:install_idx+1])
    else:
        installation_dir = bot_path.parent.parent
else:
    installation_dir = bot_path.parent.parent

system_dir = installation_dir / "_system"

# Add _system to path
if str(system_dir) not in sys.path:
    sys.path.insert(0, str(system_dir))

# Install monitoring bridge BEFORE importing selenium
try:
    from fix_direct_launches import install_monitoring_bridge
    install_monitoring_bridge()
except:
    try:
        from bot_launcher_bridge import install_monitoring_bridge
        install_monitoring_bridge()
    except:
        pass  # Silent fail - bot still works

# Now run the bot
# Change to bot's directory
os.chdir(bot_path.parent)

# Run the bot as a script (safer than exec - preserves all Python behavior)
# This ensures __name__ == "__main__" works, relative imports work, etc.
sys.argv = [str(bot_path)] + sys.argv[2:]  # Replace wrapper args with bot path
sys.path.insert(0, str(bot_path.parent))  # Add bot directory to path

# Execute the bot script
exec(open(bot_path, 'rb').read(), {'__name__': '__main__', '__file__': str(bot_path), '__package__': None})
