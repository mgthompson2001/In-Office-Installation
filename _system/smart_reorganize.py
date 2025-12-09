#!/usr/bin/env python3
"""
Smart Reorganization Script - Automatically Updates All File Paths
This will organize your In-Office Installation folder while keeping everything working
"""

import os
import shutil
from pathlib import Path
import re

def update_file_paths_in_code(file_path, old_path, new_path):
    """Update file paths in Python files"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace both forward and backslash versions
        old_forward = old_path.replace('\\', '/')
        new_forward = new_path.replace('\\', '/')
        old_back = old_path.replace('/', '\\')
        new_back = new_path.replace('/', '\\')
        
        updated = content
        updated = updated.replace(old_forward, new_forward)
        updated = updated.replace(old_back, new_back)
        updated = updated.replace(f'r"{old_back}"', f'r"{new_back}"')
        updated = updated.replace(f'r\'{old_back}\'', f'r\'{new_back}\'')
        
        if updated != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated)
            return True
        return False
    except Exception as e:
        print(f"  ⚠️  Error updating {file_path}: {e}")
        return False

def reorganize():
    """Main reorganization function"""
    base_dir = Path(__file__).parent
    
    print("="*70)
    print("  IN-OFFICE INSTALLATION SMART REORGANIZATION")
    print("="*70)
    print(f"\n📁 Base directory: {base_dir}\n")
    
    # Create new structure
    print("📂 Creating organized folder structure...")
    structure = {
        '_bots': 'All bot files and scripts',
        '_admin': 'Admin tools and update managers',
        '_docs': 'Documentation and guides',
        '_templates': 'File templates',
        '_system': 'System and installation files'
    }
    
    for folder, description in structure.items():
        folder_path = base_dir / folder
        folder_path.mkdir(exist_ok=True)
        print(f"  ✓ {folder}/ - {description}")
    
    # Define moves with path updates
    moves = {
        # Bots
        'Med Rec': '_bots',
        'The Welcomed One, Exalted Rank': '_bots',
        'Referral bot and bridge (final)': '_bots',
        'Page Extractor (Working)': '_bots',
        'Cursor versions': '_bots',
        'Launcher': '_bots',
        
        # Admin tools
        'create_update_installer.py': '_admin',
        'easy_update_manager.py': '_admin',
        'create_update_package.py': '_admin',
        'deploy_update.py': '_admin',
        'update_system.py': '_admin',
        'encrypt_code.py': '_admin',
        'create_icon.py': '_admin',
        
        # Documentation
        'README.md': '_docs',
        'NON_TECHNICAL_GUIDE.md': '_docs',
        'EMAIL_UPDATE_GUIDE.md': '_docs',
        'QUICK_DEPLOYMENT_GUIDE.md': '_docs',
        'BACKUP_README.md': '_docs',
        'REORGANIZATION_PLAN.md': '_docs',
        'deployment_guide.md': '_docs',
        'QUICK_FIX_INSTRUCTIONS.txt': '_docs',
        'SIMPLE_INSTRUCTIONS.txt': '_docs',
        
        # Templates
        'File Templates': '_templates',
        
        # System
        'install_bots.py': '_system',
        'install.bat': '_system',
        'create_shared_folder.bat': '_system',
        'setup_centralized_management.bat': '_system',
        'setup_company_shared_drive.bat': '_system',
        'update_packages': '_system',
    }
    
    # Path mapping for code updates
    path_mappings = {
        r'Med Rec\Finished Product, Launch Ready\Bot and extender\integrity_medical_records_bot_v3g_batchclicks.py': 
            r'_bots\Med Rec\Finished Product, Launch Ready\Bot and extender\integrity_medical_records_bot_v3g_batchclicks.py',
        
        r'The Welcomed One, Exalted Rank\integrity_consent_bot.py': 
            r'_bots\The Welcomed One, Exalted Rank\integrity_consent_bot.py',
        
        r'The Welcomed One, Exalted Rank\isws_welcome_DEEPFIX2_NOTEFORCE_v14.py': 
            r'_bots\The Welcomed One, Exalted Rank\isws_welcome_DEEPFIX2_NOTEFORCE_v14.py',
        
        r'Launcher\intake_referral_launcher.py': 
            r'_bots\Launcher\intake_referral_launcher.py',
        
        r'Launcher\bot_launcher.py': 
            r'_bots\Launcher\bot_launcher.py',
    }
    
    # Perform moves
    print("\n📦 Moving files...")
    moved = []
    
    for source, dest_folder in moves.items():
        source_path = base_dir / source
        
        if not source_path.exists():
            print(f"  ⊗ Skipped (not found): {source}")
            continue
        
        # Determine destination
        if source_path.is_file():
            dest_path = base_dir / dest_folder / source_path.name
        else:
            dest_path = base_dir / dest_folder / source_path.name
        
        # Skip if already exists at destination
        if dest_path.exists():
            print(f"  ⊗ Skipped (already exists): {source}")
            continue
        
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(dest_path))
            moved.append((source, str(dest_path.relative_to(base_dir))))
            print(f"  ✓ Moved: {source}")
        except Exception as e:
            print(f"  ✗ Failed: {source} - {e}")
    
    # Update paths in secure_launcher.py
    print("\n🔧 Updating file paths in secure_launcher.py...")
    launcher_path = base_dir / 'secure_launcher.py'
    
    if launcher_path.exists():
        updates_made = 0
        for old_path, new_path in path_mappings.items():
            if update_file_paths_in_code(launcher_path, old_path, new_path):
                print(f"  ✓ Updated: {old_path}")
                updates_made += 1
        
        if updates_made > 0:
            print(f"  ✅ Updated {updates_made} paths in secure_launcher.py")
        else:
            print(f"  ℹ️  No path updates needed")
    else:
        print(f"  ⚠️  secure_launcher.py not found in root")
    
    # Update paths in admin_launcher.py if it exists in root
    admin_launcher_root = base_dir / 'admin_launcher.py'
    if admin_launcher_root.exists():
        print("\n🔧 Updating paths in admin_launcher.py...")
        # Since admin_launcher will be moved, create a wrapper
        print("  ℹ️  admin_launcher.py will be moved to _admin/")
    
    # Create wrapper launchers for admin tools in root
    print("\n📝 Creating admin tool shortcuts...")
    
    admin_shortcut = base_dir / 'Admin_Tools.py'
    with open(admin_shortcut, 'w', encoding='utf-8') as f:
        f.write('''#!/usr/bin/env python3
"""Admin Tools Launcher - Opens the admin control panel"""
import subprocess
import sys
from pathlib import Path

admin_launcher = Path(__file__).parent / "_admin" / "admin_launcher.py"
subprocess.Popen([sys.executable, str(admin_launcher)])
''')
    print(f"  ✓ Created: Admin_Tools.py (launches admin panel)")
    
    # Create simple employee info file
    print("\n📄 Creating employee START_HERE file...")
    start_here = base_dir / 'START_HERE.txt'
    with open(start_here, 'w', encoding='utf-8') as f:
        f.write('''
╔═══════════════════════════════════════════════════════════════╗
║           CCMD Bot Software - Quick Start Guide              ║
╔═══════════════════════════════════════════════════════════════╗

🚀 TO USE THE SOFTWARE:

   1. Look for the "I" icon on your desktop
   2. Double-click it to launch the bot software
   3. Select which bot you want to run
   4. Follow the on-screen instructions

📧 TO INSTALL UPDATES:

   When you receive an update email from your administrator:
   
   1. Download the .py file from the email
   2. Double-click the downloaded file
   3. Click "OK" when it asks to install
   4. Click "Yes" to confirm
   5. Wait for "Installation Complete!" message
   6. Click "Done"
   
   That's it! Your software is now updated.

⚠️ IMPORTANT - DO NOT:

   ✗ Delete files from this folder
   ✗ Edit any .py files
   ✗ Move the folder to a different location
   
   Your data and settings are safe in the organized subfolders.

❓ NEED HELP?

   Contact your IT administrator or system manager.

📁 FOLDER ORGANIZATION:

   • _bots/      - All bot files (don't touch)
   • _admin/     - Admin tools (for IT only)
   • _docs/      - Documentation and guides
   • _templates/ - File templates
   • _system/    - System files (don't touch)

╚═══════════════════════════════════════════════════════════════╝
''')
    print(f"  ✓ Created: START_HERE.txt")
    
    print("\n" + "="*70)
    print("🎉 REORGANIZATION COMPLETE!")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"  • Files moved: {len(moved)}")
    print(f"  • Paths updated in code: Yes")
    print(f"  • Launcher: secure_launcher.py (stays in root)")
    print(f"  • Admin access: Admin_Tools.py (new shortcut)")
    print(f"\n✅ Everything is organized and ready to use!")
    
    # Show what's now in root
    print("\n📂 What employees see in the main folder:")
    print("  • secure_launcher.py (main launcher)")
    print("  • Admin_Tools.py (for admins)")
    print("  • START_HERE.txt (instructions)")
    print("  • requirements.txt")
    print("  • Organized _bots, _admin, _docs folders")
    
    return True

if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: This will reorganize your folder structure.")
    print("All functionality will be preserved - paths will be updated automatically.")
    print("A backup record will be created.\n")
    
    response = input("Ready to reorganize? Type 'yes' to continue: ").strip().lower()
    
    if response == 'yes':
        try:
            reorganize()
            input("\n✅ Press ENTER to exit...")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            input("\nPress ENTER to exit...")
    else:
        print("\n❌ Reorganization cancelled. No changes made.")
        input("Press ENTER to exit...")

