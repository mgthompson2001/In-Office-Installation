#!/usr/bin/env python3
"""
Verify Employee Installation - Check if system is configured correctly after INSTALL_BOTS.bat
This script verifies that data collection and transfer are properly set up.
Works universally on any employee computer.
"""

import sys
import json
from pathlib import Path

# Get installation directory (parent of _tools)
try:
    installation_dir = Path(__file__).parent.parent.parent
except:
    # Fallback: try to find it from common locations
    import os
    cwd = Path(os.getcwd())
    # Try to find In-Office Installation directory
    possible_paths = [
        cwd,
        cwd.parent if cwd.name == "_tools" else None,
        Path.home() / "Desktop" / "In-Office Installation",
        Path("C:/Users") / os.getlogin() / "Desktop" / "In-Office Installation",
    ]
    installation_dir = None
    for path in possible_paths:
        if path and path.exists() and (path / "INSTALL_BOTS.bat").exists():
            installation_dir = path
            break
    
    if not installation_dir:
        print("ERROR: Could not find installation directory!")
        print(f"Current directory: {cwd}")
        print("Please run this script from the installation directory or specify the path.")
        sys.exit(1)

print("=" * 70)
print("EMPLOYEE INSTALLATION VERIFICATION")
print("=" * 70)
print()
print(f"Installation directory: {installation_dir}")
print()

# Add AI directory to path
ai_dir = installation_dir / "AI"
if ai_dir.exists() and str(ai_dir) not in sys.path:
    sys.path.insert(0, str(ai_dir))

# Initialize variables (in case of errors)
mode = 'NOT SET'
computer_id = 'NOT SET'
central_path = 'NOT SET'
transfer_interval = 'NOT SET'
config = {}

# Check 1: System Configuration
print("1. CHECKING SYSTEM CONFIGURATION...")
try:
    try:
        from monitoring.system_config import (
            load_config, 
            is_employee_computer, 
            is_central_computer, 
            get_central_data_path, 
            get_computer_id
        )
        config = load_config(installation_dir)
    except ImportError:
        print("   ⚠️  Could not import monitoring modules")
        print("   Checking config file directly...")
        
        # Try to read config file directly
        config_file = ai_dir / "monitoring" / "system_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}
            print("   ❌ Config file not found - system not configured!")
            print("      Run INSTALL_BOTS.bat first to configure the system.")
    except Exception as e:
        print(f"   ⚠️  Error importing config module: {e}")
        # Try to read config file directly as fallback
        config_file = ai_dir / "monitoring" / "system_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                config = {}
        else:
            config = {}
    
    # Extract values with defaults
    mode = config.get('mode', 'NOT SET')
    computer_id = config.get('computer_id', 'NOT SET')
    central_path = config.get('central_data_path', 'NOT SET')
    transfer_interval = config.get('transfer_interval_hours', 'NOT SET')
    
    print(f"   Mode: {mode}")
    print(f"   Computer ID: {computer_id}")
    print(f"   Central Data Path: {central_path}")
    print(f"   Transfer Interval: {transfer_interval} hours")
    print()
    
    if mode == "employee":
        print("   ✅ Employee mode is configured")
        if central_path and central_path != "NOT SET":
            try:
                central_path_obj = Path(central_path)
                # For network paths, try to access parent
                if central_path_obj.exists():
                    print(f"   ✅ Central data folder exists: {central_path}")
                elif central_path_obj.parent.exists():
                    print(f"   ✅ Central data folder parent exists (will be created automatically)")
                else:
                    print(f"   ⚠️  Central data folder does not exist: {central_path}")
                    print("      (It will be created automatically when data is transferred)")
            except Exception as e:
                print(f"   ⚠️  Could not check central path: {e}")
                print(f"      Path: {central_path}")
        else:
            print("   ❌ Central data path is not configured!")
            print("      Run: python _tools\\config\\CONFIGURE_EMPLOYEE_MODE.py")
    elif mode == "central":
        print("   ⚠️  This computer is configured as CENTRAL, not EMPLOYEE")
        print("      If this is an employee computer, run:")
        print("      python _tools\\config\\CONFIGURE_EMPLOYEE_MODE.py")
    else:
        print("   ❌ System mode is not configured!")
        print("      Run INSTALL_BOTS.bat to configure automatically, or:")
        print("      python _tools\\config\\CONFIGURE_EMPLOYEE_MODE.py")
        
except Exception as e:
    print(f"   ❌ Error checking configuration: {e}")
    import traceback
    traceback.print_exc()

print()

# Check 2: Data Collection Setup
print("2. CHECKING DATA COLLECTION SETUP...")
try:
    # Check if cleanup system is available
    bots_dir = installation_dir / "_bots"
    if bots_dir.exists():
        # Try multiple possible locations for init_passive_cleanup.py
        possible_init_paths = [
            bots_dir / "Billing Department" / "init_passive_cleanup.py",
            bots_dir / "init_passive_cleanup.py",
            installation_dir / "_bots" / "Billing Department" / "init_passive_cleanup.py",
        ]
        
        init_cleanup_found = False
        for init_path in possible_init_paths:
            if init_path.exists():
                print(f"   ✅ Passive cleanup system found: {init_path.name}")
                init_cleanup_found = True
                break
        
        if not init_cleanup_found:
            print("   ⚠️  Passive cleanup system not found")
            print("      (This may be OK if using a different structure)")
    
    # Check if AI monitoring is set up
    monitoring_dir = ai_dir / "monitoring"
    if monitoring_dir.exists():
        print("   ✅ AI monitoring directory exists")
        
        # Check key files
        data_cleanup = monitoring_dir / "data_cleanup.py"
        data_transfer = monitoring_dir / "data_transfer.py"
        system_config = monitoring_dir / "system_config.py"
        
        files_found = 0
        if data_cleanup.exists():
            print("   ✅ Data cleanup module found")
            files_found += 1
        if data_transfer.exists():
            print("   ✅ Data transfer module found")
            files_found += 1
        if system_config.exists():
            print("   ✅ System configuration module found")
            files_found += 1
        
        if files_found == 0:
            print("   ⚠️  No monitoring modules found in AI/monitoring/")
    else:
        print("   ⚠️  AI monitoring directory not found")
        print(f"      Expected: {monitoring_dir}")
        
except Exception as e:
    print(f"   ⚠️  Error checking data collection: {e}")
    import traceback
    traceback.print_exc()

print()

# Check 3: Training Data Directory
print("3. CHECKING TRAINING DATA DIRECTORY...")
try:
    training_data_dir = ai_dir / "training_data"
    if training_data_dir.exists():
        print(f"   ✅ Training data directory exists: {training_data_dir.name}")
        
        # Check for existing data
        training_files = list(training_data_dir.glob("*.json"))
        training_files.extend(list(training_data_dir.glob("*.json.gz")))
        
        if training_files:
            print(f"   ✅ Found {len(training_files)} training data files")
            try:
                total_size = sum(f.stat().st_size for f in training_files) / (1024 * 1024)
                print(f"   ✅ Total training data: {total_size:.2f} MB")
            except:
                print("   ✅ Training data files found (size calculation failed)")
        else:
            print("   ℹ️  No training data files yet (this is normal for new installations)")
    else:
        print("   ⚠️  Training data directory does not exist")
        print(f"      Expected: {training_data_dir}")
        print("      (It will be created automatically when data is collected)")
        
except Exception as e:
    print(f"   ⚠️  Error checking training data: {e}")

print()

# Check 4: Last Transfer Status
print("4. CHECKING TRANSFER STATUS...")
try:
    last_transfer_file = installation_dir / "AI" / "monitoring" / "last_transfer.json"
    if last_transfer_file.exists():
        try:
            with open(last_transfer_file, 'r', encoding='utf-8') as f:
                last_transfer = json.load(f)
            last_time = last_transfer.get('last_transfer', last_transfer.get('timestamp', 'Unknown'))
            print(f"   ✅ Last transfer: {last_time}")
        except Exception as e:
            print(f"   ⚠️  Could not read transfer file: {e}")
    else:
        print("   ℹ️  No transfers yet (this is normal for new installations)")
        print("      Data will transfer automatically when bots run")
        
except Exception as e:
    print(f"   ⚠️  Error checking transfer status: {e}")

print()

# Check 5: Bot Integration
print("5. CHECKING BOT INTEGRATION...")
try:
    # Check if _bots/__init__.py has cleanup integration
    bots_init = installation_dir / "_bots" / "__init__.py"
    if bots_init.exists():
        try:
            with open(bots_init, 'r', encoding='utf-8') as f:
                content = f.read()
                if "init_passive_cleanup" in content or "SystemCleanup" in content or "_init_system_cleanup" in content:
                    print("   ✅ Bot integration is configured")
                    print("      Cleanup will run automatically when bots start")
                else:
                    print("   ⚠️  Bot integration may not be configured")
                    print("      Expected to find 'init_passive_cleanup' or 'SystemCleanup' in __init__.py")
        except Exception as e:
            print(f"   ⚠️  Could not read bot init file: {e}")
    else:
        print("   ⚠️  Bot initialization file not found")
        print(f"      Expected: {bots_init}")
        
except Exception as e:
    print(f"   ⚠️  Error checking bot integration: {e}")

print()

# Check 6: Network/Path Accessibility
print("6. CHECKING CENTRAL DATA PATH ACCESSIBILITY...")
try:
    if mode == "employee" and central_path and central_path != "NOT SET":
        try:
            central_path_obj = Path(central_path)
            
            # Try to create a test file
            try:
                test_file = central_path_obj / f"test_{computer_id}.txt"
                test_file.parent.mkdir(parents=True, exist_ok=True)
                test_file.write_text("test")
                test_file.unlink()  # Delete test file
                
                print(f"   ✅ Can write to central data folder: {central_path}")
            except PermissionError:
                print(f"   ❌ Permission denied: Cannot write to {central_path}")
                print("      Check folder permissions and network access")
            except Exception as e:
                print(f"   ⚠️  Cannot write to central data folder: {e}")
                print("      (This may be OK if the folder doesn't exist yet)")
                print("      The folder will be created automatically on first transfer")
        except Exception as e:
            print(f"   ⚠️  Error checking path accessibility: {e}")
    else:
        print("   ⚠️  Skipping (not in employee mode or path not configured)")
        
except Exception as e:
    print(f"   ⚠️  Error checking path accessibility: {e}")

print()

# Summary
print("=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)
print()

if mode == "employee" and central_path and central_path != "NOT SET":
    print("✅ SYSTEM IS CONFIGURED AS EMPLOYEE COMPUTER")
    print()
    print("What happens next:")
    print("  1. When you run any bot, data collection starts automatically")
    print("  2. Data is collected in the background (non-blocking)")
    print("  3. Every 24 hours (or configured interval), data transfers to:")
    print(f"     {central_path}")
    print("  4. Training happens on the central computer, not here")
    print()
    print("To test the system:")
    print("  1. Run any bot (e.g., Medisoft Billing Bot)")
    print("  2. Wait a few minutes for data collection")
    print("  3. Check transfer status with this script again")
    print()
    print("✅ Installation appears to be working correctly!")
else:
    print("⚠️  SYSTEM NEEDS CONFIGURATION")
    print()
    if mode != "employee":
        print("System is not configured as an employee computer.")
    if not central_path or central_path == "NOT SET":
        print("Central data path is not configured.")
    print()
    print("To fix this:")
    print("  1. Run INSTALL_BOTS.bat again (if you haven't)")
    print("  2. Or manually configure:")
    print("     python _tools\\config\\CONFIGURE_EMPLOYEE_MODE.py")
    print()
    print("You'll need:")
    print("  - Central data folder path: G:\\Company\\Software\\Training Data")
    print("  - Transfer interval (default: 24 hours)")

print()
print("=" * 70)
input("Press ENTER to exit...")
