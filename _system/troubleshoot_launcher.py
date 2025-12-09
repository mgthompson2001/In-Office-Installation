#!/usr/bin/env python3
"""
CCMD Bot Launcher Troubleshooting Script
Diagnoses common installation and launch issues
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header():
    print("=" * 60)
    print("CCMD Bot Launcher Troubleshooter")
    print("=" * 60)
    print()

def check_python():
    """Check Python installation"""
    print("🐍 Checking Python...")
    print(f"   Version: {sys.version}")
    print(f"   Executable: {sys.executable}")
    print(f"   Platform: {sys.platform}")
    return True

def check_installation_structure():
    """Check if installation files are present"""
    print("\n📁 Checking installation structure...")
    
    install_dir = Path(__file__).parent.parent
    launcher_path = install_dir / "_system" / "secure_launcher.py"
    icon_path = install_dir / "_system" / "ccmd_bot_icon.ico"
    
    print(f"   Installation directory: {install_dir}")
    print(f"   Launcher exists: {launcher_path.exists()}")
    print(f"   Icon exists: {icon_path.exists()}")
    
    if not launcher_path.exists():
        print("   ❌ Launcher file missing!")
        return False
    
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'tkinter', 'selenium', 'pandas', 'openpyxl', 
        'Pillow', 'requests', 'beautifulsoup4'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
            elif package == 'selenium':
                import selenium
            elif package == 'pandas':
                import pandas
            elif package == 'openpyxl':
                import openpyxl
            elif package == 'Pillow':
                import PIL
            elif package == 'requests':
                import requests
            elif package == 'beautifulsoup4':
                import bs4
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n   Missing packages: {', '.join(missing_packages)}")
        print("   Run: pip install " + " ".join(missing_packages))
        return False
    
    return True

def test_launcher_import():
    """Test if launcher can be imported"""
    print("\n🧪 Testing launcher import...")
    
    install_dir = Path(__file__).parent.parent
    launcher_path = install_dir / "_system" / "secure_launcher.py"
    
    try:
        # Add the _system directory to Python path
        sys.path.insert(0, str(install_dir / "_system"))
        
        # Try to import
        import secure_launcher
        print("   ✅ Launcher imports successfully")
        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False

def test_launcher_startup():
    """Test if launcher can start (without GUI)"""
    print("\n🚀 Testing launcher startup...")
    
    install_dir = Path(__file__).parent.parent
    launcher_path = install_dir / "_system" / "secure_launcher.py"
    
    try:
        # Try to run launcher with --test flag (if it exists)
        result = subprocess.run([
            sys.executable, str(launcher_path), "--test"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("   ✅ Launcher starts successfully")
            return True
        else:
            print(f"   ⚠️  Launcher returned code {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("   ⚠️  Launcher started but timed out (this might be normal)")
        return True
    except Exception as e:
        print(f"   ❌ Startup test failed: {e}")
        return False

def check_desktop_shortcut():
    """Check if desktop shortcut exists and is valid"""
    print("\n🔗 Checking desktop shortcut...")
    
    desktop = Path.home() / "Desktop"
    shortcut_paths = [
        desktop / "Automation Hub.lnk",
        desktop / "CCMD Automation Hub.lnk",  # Check for old name too
        desktop / "Automation Hub.bat"
    ]
    
    found_shortcuts = []
    for shortcut in shortcut_paths:
        if shortcut.exists():
            found_shortcuts.append(shortcut)
            print(f"   ✅ Found: {shortcut.name}")
        else:
            print(f"   ❌ Missing: {shortcut.name}")
    
    if not found_shortcuts:
        print("   ❌ No desktop shortcuts found!")
        return False
    
    return True

def main():
    print_header()
    
    all_good = True
    
    # Run all checks
    all_good &= check_python()
    all_good &= check_installation_structure()
    all_good &= check_dependencies()
    all_good &= test_launcher_import()
    all_good &= test_launcher_startup()
    all_good &= check_desktop_shortcut()
    
    print("\n" + "=" * 60)
    if all_good:
        print("✅ All checks passed! The launcher should work properly.")
    else:
        print("❌ Some issues found. Please address the problems above.")
        print("\n💡 Common fixes:")
        print("   1. Run: pip install -r requirements.txt")
        print("   2. Re-run the installation script")
        print("   3. Check that all files are present in the installation folder")
    print("=" * 60)
    
    input("\nPress ENTER to exit...")

if __name__ == "__main__":
    main()
