#!/usr/bin/env python3
"""Create a desktop shortcut for Master AI Dashboard."""

import os
import sys
from pathlib import Path


def create_shortcut(install_dir: Path = None):
    if install_dir is None:
        install_dir = Path(__file__).parent.parent

    ai_dir = install_dir / "AI"
    target = ai_dir / "LAUNCH_MASTER_AI_DASHBOARD.bat"
    robot_icon = install_dir / "_system" / "master_ai_robot.ico"
    legacy_icon = install_dir / "_system" / "ccmd_bot_icon.ico"
    shortcut_name = "Master AI Dashboard.lnk"
    icon_path = robot_icon if robot_icon.exists() else legacy_icon
    target_str = str(target).replace('\\', '\\\\')
    ai_dir_str = str(ai_dir).replace('\\', '\\\\')
    icon_str = str(icon_path).replace('\\', '\\\\')

    # Method 1: win32com
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = shell.SpecialFolders("Desktop")
        shortcut_path = os.path.join(desktop, shortcut_name)
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = str(target)
        shortcut.WorkingDirectory = str(ai_dir)
        shortcut.Description = "Master AI Dashboard"
        if icon_path.exists():
            shortcut.IconLocation = str(icon_path)
        shortcut.save()
        return True, shortcut_path
    except Exception:
        pass

    # Method 2: VBScript fallback
    vbs_content = f"""Set WshShell = CreateObject(\"WScript.Shell\")
desktopPath = WshShell.SpecialFolders(\"Desktop\")
shortcutPath = desktopPath & \"\\{shortcut_name}\"
Set shortcut = WshShell.CreateShortcut(shortcutPath)
shortcut.TargetPath = \"{target_str}\"
shortcut.WorkingDirectory = \"{ai_dir_str}\"
shortcut.Description = \"Master AI Dashboard\"
shortcut.IconLocation = \"{icon_str},0\"
shortcut.Save
"""

    try:
        import subprocess
        temp_vbs = Path(os.getenv("TEMP", "C:/Temp")) / "create_master_ai_dashboard_shortcut.vbs"
        temp_vbs.write_text(vbs_content, encoding="utf-8")
        result = subprocess.run(['cscript', '//nologo', str(temp_vbs)], capture_output=True, text=True, timeout=10)
        temp_vbs.unlink(missing_ok=True)
        if result.returncode == 0:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            return True, os.path.join(desktop, shortcut_name)
        else:
            return False, result.stderr
    except Exception as exc:
        return False, str(exc)


if __name__ == "__main__":
    success, info = create_shortcut()
    if success:
        print(f"Shortcut created: {info}")
    else:
        print(f"Failed to create shortcut: {info}")

