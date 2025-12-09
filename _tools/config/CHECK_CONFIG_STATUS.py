#!/usr/bin/env python3
"""Check system configuration status"""

import sys
from pathlib import Path

# Get installation directory
installation_dir = Path(__file__).parent.parent.parent

# Add AI directory to path
ai_dir = installation_dir / "AI"
if ai_dir.exists() and str(ai_dir) not in sys.path:
    sys.path.insert(0, str(ai_dir))

try:
    from monitoring.system_config import (
        load_config, 
        is_employee_computer, 
        is_central_computer, 
        get_central_data_path, 
        get_computer_id
    )
    
    config = load_config(installation_dir)
    
    print("=" * 70)
    print("SYSTEM CONFIGURATION STATUS")
    print("=" * 70)
    print()
    print(f"Mode: {config.get('mode', 'NOT SET')}")
    print(f"Computer ID: {config.get('computer_id', 'NOT SET')}")
    print(f"Central Data Path: {config.get('central_data_path', 'NOT SET')}")
    print(f"Transfer Interval: {config.get('transfer_interval_hours', 'NOT SET')} hours")
    print()
    print("Status Checks:")
    print(f"  Is Employee Computer: {is_employee_computer(installation_dir)}")
    print(f"  Is Central Computer: {is_central_computer(installation_dir)}")
    print()
    
    central_path = get_central_data_path(installation_dir)
    if central_path:
        central_path = Path(central_path)
        print(f"Central Path Resolved: {central_path}")
        print(f"Central Path Exists: {central_path.exists()}")
        
        if not central_path.exists():
            print()
            print("⚠️  WARNING: Central data folder does not exist!")
            print(f"   Path: {central_path}")
            print("   The folder will be created automatically when data is transferred.")
            print("   Or you can create it manually.")
        else:
            print(f"✅ Central data folder exists and is accessible")
    else:
        print("⚠️  No central data path configured")
    
    print()
    print("=" * 70)
    
    # Verify the path is correct
    expected_path = Path("G:/Company/Software/Training Data")
    if central_path and Path(central_path) == expected_path:
        print("✅ Configuration matches requested path!")
    elif central_path:
        print(f"⚠️  Path in config: {central_path}")
        print(f"   Expected: {expected_path}")
    
except Exception as e:
    print(f"❌ Error checking configuration: {e}")
    import traceback
    traceback.print_exc()

