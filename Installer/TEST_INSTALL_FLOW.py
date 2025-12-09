#!/usr/bin/env python3
"""
Test script to verify install_for_employee.py will work correctly.
This validates paths, imports, and critical dependencies.
"""

import sys
import os
from pathlib import Path

def test_path_calculations():
    """Test that path calculations from Installer folder are correct."""
    print("=" * 60)
    print("TEST 1: Path Calculations")
    print("=" * 60)
    
    # Simulate being in Installer folder (where install_for_employee.py is)
    installer_dir = Path(__file__).parent
    installation_dir = installer_dir.parent
    system_dir = installation_dir / "_system"
    bots_dir = installation_dir / "_bots"
    ai_dir = installation_dir / "AI"
    
    print(f"Installer dir: {installer_dir}")
    print(f"Installation dir: {installation_dir}")
    print(f"System dir: {system_dir}")
    print(f"Bots dir: {bots_dir}")
    print(f"AI dir: {ai_dir}")
    print()
    
    # Check critical files/directories exist
    checks = {
        "install_for_employee.py": installer_dir / "install_for_employee.py",
        "_system directory": system_dir,
        "_bots directory": bots_dir,
        "AI directory": ai_dir,
        "system requirements.txt": system_dir / "requirements.txt",
        "secure_launcher.py": system_dir / "secure_launcher.py",
        "create_bat_wrappers.py": system_dir / "create_bat_wrappers.py",
        "system_config.py": ai_dir / "monitoring" / "system_config.py",
    }
    
    all_pass = True
    for name, path in checks.items():
        exists = path.exists()
        status = "[OK]" if exists else "[MISSING]"
        print(f"  {status} {name}: {path}")
        if not exists:
            all_pass = False
    
    print()
    return all_pass

def test_imports():
    """Test that critical imports will work."""
    print("=" * 60)
    print("TEST 2: Import Validation")
    print("=" * 60)
    
    installer_dir = Path(__file__).parent
    installation_dir = installer_dir.parent
    ai_dir = installation_dir / "AI"
    
    # Add AI to path (like install script does)
    import sys as sys_module
    if str(ai_dir) not in sys_module.path:
        sys_module.path.insert(0, str(ai_dir))
    
    import_tests = []
    
    # Test standard library imports (should always work)
    try:
        import subprocess
        import platform
        import os
        import sys
        print("  [OK] Standard library imports (subprocess, platform, os, sys)")
        import_tests.append(True)
    except Exception as e:
        print(f"  [FAIL] Standard library imports failed: {e}")
        import_tests.append(False)
    
    # Test system_config import (critical for employee mode)
    try:
        from monitoring.system_config import configure_employee_mode
        print("  [OK] system_config module import successful")
        print(f"    Function available: configure_employee_mode")
        import_tests.append(True)
    except Exception as e:
        print(f"  [FAIL] system_config import failed: {e}")
        import_tests.append(False)
    
    # Test win32com (optional but preferred for shortcuts)
    try:
        import win32com.client
        print("  [OK] win32com import successful (icon handling will work)")
        import_tests.append(True)
    except ImportError:
        print("  [WARN] win32com not available (will use VBScript fallback)")
        import_tests.append(True)  # This is OK, not a failure
    
    # Test PIL (optional for PNG to ICO conversion)
    try:
        from PIL import Image
        print("  [OK] PIL/Pillow import successful (PNG to ICO conversion available)")
        import_tests.append(True)
    except ImportError:
        print("  [WARN] PIL/Pillow not available (PNG conversion won't work)")
        import_tests.append(True)  # This is OK, not a failure
    
    print()
    return all(import_tests)

def test_configure_employee_mode():
    """Test that configure_employee_mode function exists and is callable."""
    print("=" * 60)
    print("TEST 3: configure_employee_mode Function")
    print("=" * 60)
    
    installer_dir = Path(__file__).parent
    installation_dir = installer_dir.parent
    ai_dir = installation_dir / "AI"
    
    if str(ai_dir) not in sys.path:
        sys.path.insert(0, str(ai_dir))
    
    try:
        from monitoring.system_config import configure_employee_mode
        import inspect
        
        # Check function signature
        sig = inspect.signature(configure_employee_mode)
        params = list(sig.parameters.keys())
        print(f"  [OK] Function signature: configure_employee_mode({', '.join(params)})")
        
        # Expected: (installation_dir, central_data_path, transfer_interval_hours)
        expected_params = ['installation_dir', 'central_data_path', 'transfer_interval_hours']
        if params == expected_params:
            print("  [OK] Function parameters match expected signature")
            return True
        else:
            print(f"  [FAIL] Function parameters don't match!")
            print(f"    Expected: {expected_params}")
            print(f"    Got: {params}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error checking function: {e}")
        return False

def test_script_syntax():
    """Test that install_for_employee.py has valid Python syntax."""
    print("=" * 60)
    print("TEST 4: Script Syntax Validation")
    print("=" * 60)
    
    installer_dir = Path(__file__).parent
    script_path = installer_dir / "install_for_employee.py"
    
    if not script_path.exists():
        print(f"  [FAIL] Script not found: {script_path}")
        return False
    
    try:
        # Compile to check syntax
        with open(script_path, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, str(script_path), 'exec')
        print(f"  [OK] Script syntax is valid")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] Syntax error: {e}")
        print(f"    Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("INSTALLATION SCRIPT VALIDATION")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Path Calculations", test_path_calculations()))
    results.append(("Imports", test_imports()))
    results.append(("configure_employee_mode", test_configure_employee_mode()))
    results.append(("Script Syntax", test_script_syntax()))
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    
    all_pass = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {name}")
        if not passed:
            all_pass = False
    
    print()
    if all_pass:
        print("[SUCCESS] ALL TESTS PASSED - Installation script should work correctly!")
        return 0
    else:
        print("[ERROR] SOME TESTS FAILED - Installation script may have issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())

