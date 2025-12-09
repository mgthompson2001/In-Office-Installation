#!/usr/bin/env python3
"""Admin Tools Shortcut - Quick access to admin control panel"""
import subprocess
import sys
from pathlib import Path

# Launch the admin control panel
admin_launcher = Path(__file__).parent / "_admin" / "admin_launcher.py"

if admin_launcher.exists():
    subprocess.Popen([sys.executable, str(admin_launcher)])
else:
    print(f"Error: Admin launcher not found at {admin_launcher}")
    input("Press ENTER to exit...")

