#!/usr/bin/env python3
"""
Bot Installation Script - Enterprise Deployment
Automatically installs all dependencies when bots are installed on employee computers.
Includes user registration for data centralization.
"""

import os
import sys
from pathlib import Path

# Import auto installer
try:
    from auto_install_dependencies import AutoDependencyInstaller
    AUTO_INSTALL_AVAILABLE = True
except ImportError:
    AUTO_INSTALL_AVAILABLE = False
    AutoDependencyInstaller = None

# Import user registration
try:
    from user_registration import UserRegistration
    USER_REGISTRATION_AVAILABLE = True
except ImportError:
    USER_REGISTRATION_AVAILABLE = False
    UserRegistration = None

def install_bots():
    """Install bots and all dependencies"""
    print("=" * 70)
    print("Enterprise Bot Installation")
    print("=" * 70)
    print("\nThis script will install all dependencies for the enterprise AI system.")
    print("This may take a few minutes...\n")
    
    # Get installation directory
    installation_dir = Path(__file__).parent.parent
    system_dir = installation_dir / "_system"
    
    # Step 1: User Registration
    print("=" * 70)
    print("STEP 1: User Registration")
    print("=" * 70)
    print("\nTo centralize data collection and track usage, please register:")
    print("(This information is stored securely and HIPAA-compliant)\n")
    
    # Check if installation is in OneDrive
    installation_path = str(installation_dir).lower()
    
    if "onedrive" in installation_path:
        print("[OK] Installation folder is in OneDrive - data will sync automatically!")
    else:
        print("[WARNING] Installation folder is NOT in OneDrive!")
        print("  For data to sync to admin, please move this folder to OneDrive.")
        print("  Current location:", installation_dir)
        print("\n  Recommended: Move 'In-Office Installation' folder to OneDrive folder")
        print("  Then run this installation again from the OneDrive location.\n")
    
    print()
    
    if USER_REGISTRATION_AVAILABLE:
        user_reg = UserRegistration(installation_dir)
        
        # Check if already registered
        existing_user = user_reg.get_local_user()
        if existing_user:
            print(f"\n✓ Already registered as: {existing_user['user_name']}")
            print(f"  Computer: {existing_user['computer_name']}")
            response = input("\nDo you want to re-register? (y/n): ").strip().lower()
            if response != 'y':
                print("✓ Using existing registration\n")
                user_name = existing_user['user_name']
            else:
                user_name = input("\nEnter your name: ").strip()
                if not user_name:
                    print("⚠ No name entered. Using default registration.")
                    user_name = f"User_{os.getenv('USERNAME', 'Unknown')}"
        else:
            user_name = input("\nEnter your name: ").strip()
            if not user_name:
                print("⚠ No name entered. Using default registration.")
                user_name = f"User_{os.getenv('USERNAME', 'Unknown')}"
        
        # Register user
        registration = user_reg.register_user(user_name)
        print(f"\n✓ Registration complete!")
        print(f"  Name: {registration['user_name']}")
        print(f"  Computer: {registration['computer_name']}")
        print(f"  Computer ID: {registration['computer_id']}")
        print(f"\n✓ Data will be centralized in OneDrive for AI training.\n")
    else:
        print("\n⚠ User registration not available. Continuing with installation...\n")
    
    # Step 2: Install Dependencies
    print("=" * 70)
    print("STEP 2: Installing Dependencies")
    print("=" * 70)
    print("\nInstalling all dependencies for the enterprise AI system...\n")
    
    if AUTO_INSTALL_AVAILABLE:
        installer = AutoDependencyInstaller(installation_dir)
        success = installer.install_all_dependencies()
        
        if success:
            print("\n✓ All dependencies installed successfully!")
            print("\nNext steps:")
            print("1. Install Ollama (for local AI): https://ollama.ai")
            print("2. Run: ollama serve")
            print("3. Pull model: ollama pull llama2")
            print("\nYou can now use the Automation Hub!")
        else:
            print("\n⚠ Some dependencies may not have installed.")
            print("Please check the log file: _system/dependency_install.log")
    else:
        print("\n✗ Auto installer not available.")
        print("Please install dependencies manually:")
        print("  pip install -r _system/requirements.txt")
        print("  pip install -r _system/requirements_enterprise.txt")
    
    # Step 3: Create Desktop Shortcut
    print("=" * 70)
    print("STEP 3: Creating Desktop Shortcut")
    print("=" * 70)
    print("\nCreating desktop shortcut for Automation Hub...\n")
    
    try:
        from create_desktop_shortcut import create_desktop_shortcut
        success, result = create_desktop_shortcut(installation_dir)
        
        if success:
            print(f"✓ Desktop shortcut created successfully!")
            print(f"  Location: {result}")
            print(f"  Name: Automation Hub.lnk")
            print(f"\n✓ You can now launch Automation Hub from your desktop!\n")
        else:
            print(f"⚠ Could not create desktop shortcut automatically.")
            print(f"  Error: {result}")
            print(f"\n  To create manually:")
            print(f"  1. Right-click on desktop")
            print(f"  2. New → Shortcut")
            print(f"  3. Browse to: {system_dir / 'launch_automation_hub.vbs'}")
            print(f"  4. Name it: Automation Hub\n")
    except ImportError:
        # Fallback: Use VBScript directly
        try:
            import subprocess
            vbs_script = installation_dir / "_system" / "create_desktop_shortcut_universal.vbs"
            if vbs_script.exists():
                result = subprocess.run(
                    ['cscript', '//nologo', str(vbs_script)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    print("✓ Desktop shortcut created successfully!")
                    print("  Name: Automation Hub.lnk")
                    print("  Location: Desktop\n")
                else:
                    print("⚠ Could not create desktop shortcut automatically.")
                    print("  Please create manually using create_desktop_shortcut_universal.vbs\n")
            else:
                print("⚠ Desktop shortcut creation script not found.")
                print("  Please create shortcut manually.\n")
        except Exception as e:
            print(f"⚠ Error creating desktop shortcut: {e}")
            print("  Please create shortcut manually.\n")
    
    print("=" * 70)
    print("✓ Installation Complete!")
    print("=" * 70)
    print("\nYour data will be automatically centralized in OneDrive.")
    print("This allows the AI to learn from all employee usage patterns.")
    print("\n✓ Desktop shortcut created: Automation Hub.lnk")
    print("  You can launch Automation Hub from your desktop!\n")
    input("\nPress ENTER to close...")

if __name__ == "__main__":
    install_bots()

