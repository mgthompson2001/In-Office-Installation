#!/usr/bin/env python3
"""
Configure Employee Mode - Set up data transfer to central location.
"""

import sys
from pathlib import Path

# Get installation directory (parent of _tools)
installation_dir = Path(__file__).parent.parent.parent

# Add AI directory to path
ai_dir = installation_dir / "AI"
if ai_dir.exists() and str(ai_dir) not in sys.path:
    sys.path.insert(0, str(ai_dir))

try:
    from monitoring.system_config import configure_employee_mode, configure_central_mode
    
    print("=" * 70)
    print("BOT SYSTEM CONFIGURATION")
    print("=" * 70)
    print()
    print("Choose configuration mode:")
    print("  1. Employee Computer (collects data, transfers to central)")
    print("  2. Central Computer (receives data, runs training)")
    print()
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\n" + "=" * 70)
        print("EMPLOYEE COMPUTER CONFIGURATION")
        print("=" * 70)
        print("\nThis computer will collect data and transfer it to a central location.")
        print("Training will happen on the central computer, not here.")
        print()
        
        central_path = input("Enter central data folder path: ").strip()
        if not central_path:
            print("❌ No path provided. Exiting.")
            sys.exit(1)
        
        interval_input = input("Transfer interval in hours [24]: ").strip()
        interval_hours = int(interval_input) if interval_input else 24
        
        if configure_employee_mode(installation_dir, central_path, interval_hours):
            print(f"\n✅ Employee mode configured!")
            print(f"   Central path: {central_path}")
            print(f"   Transfer interval: {interval_hours} hours")
        else:
            print("\n❌ Configuration failed!")
            sys.exit(1)
            
    elif choice == "2":
        print("\n" + "=" * 70)
        print("CENTRAL COMPUTER CONFIGURATION")
        print("=" * 70)
        print("\nThis computer will receive data from employee computers and run training.")
        print()
        
        central_path = input("Enter central data folder path (where employee data arrives) [optional]: ").strip()
        
        if configure_central_mode(installation_dir):
            print("\n✅ Central mode configured!")
            if central_path:
                # Save central path for collection
                from monitoring.system_config import load_config, save_config
                config = load_config(installation_dir)
                config["central_data_path"] = central_path
                save_config(installation_dir, config)
                print(f"   Central data path: {central_path}")
        else:
            print("\n❌ Configuration failed!")
            sys.exit(1)
    else:
        print("❌ Invalid choice")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ Error: Could not import configuration module: {e}")
    print("Make sure you're running this from the installation directory.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("\n✅ Configuration complete!")

