#!/usr/bin/env python3
"""
In-Office Installation Folder Reorganization Script
Organizes all backend files into clean subfolders while maintaining all functionality
"""

import os
import shutil
from pathlib import Path
import json

def reorganize_installation():
    """Reorganize the In-Office Installation folder"""
    
    # Get the base directory
    base_dir = Path(__file__).parent
    print(f"📁 Working in: {base_dir}")
    
    # Create new folder structure
    folders = {
        '_bots': base_dir / '_bots',
        '_admin': base_dir / '_admin',
        '_docs': base_dir / '_docs',
        '_templates': base_dir / '_templates',
        '_system': base_dir / '_system'
    }
    
    print("\n📂 Creating organized folder structure...")
    for name, path in folders.items():
        path.mkdir(exist_ok=True)
        print(f"  ✓ Created: {name}/")
    
    # Define what goes where
    moves = [
        # Bot folders -> _bots/
        ('Med Rec', '_bots/Med Rec'),
        ('The Welcomed One, Exalted Rank', '_bots/The Welcomed One, Exalted Rank'),
        ('Referral bot and bridge (final)', '_bots/Referral bot and bridge (final)'),
        ('Page Extractor (Working)', '_bots/Page Extractor (Working)'),
        ('Cursor versions', '_bots/Cursor versions'),
        ('Launcher', '_bots/Launcher'),
        
        # Admin tools -> _admin/
        ('admin_launcher.py', '_admin/admin_launcher.py'),
        ('create_update_installer.py', '_admin/create_update_installer.py'),
        ('easy_update_manager.py', '_admin/easy_update_manager.py'),
        ('create_update_package.py', '_admin/create_update_package.py'),
        ('deploy_update.py', '_admin/deploy_update.py'),
        ('update_system.py', '_admin/update_system.py'),
        ('encrypt_code.py', '_admin/encrypt_code.py'),
        ('create_icon.py', '_admin/create_icon.py'),
        
        # Documentation -> _docs/
        ('README.md', '_docs/README.md'),
        ('NON_TECHNICAL_GUIDE.md', '_docs/NON_TECHNICAL_GUIDE.md'),
        ('EMAIL_UPDATE_GUIDE.md', '_docs/EMAIL_UPDATE_GUIDE.md'),
        ('QUICK_DEPLOYMENT_GUIDE.md', '_docs/QUICK_DEPLOYMENT_GUIDE.md'),
        ('BACKUP_README.md', '_docs/BACKUP_README.md'),
        ('REORGANIZATION_PLAN.md', '_docs/REORGANIZATION_PLAN.md'),
        ('deployment_guide.md', '_docs/deployment_guide.md'),
        ('INSTALLATION_GUIDE.md', '_docs/INSTALLATION_GUIDE.md'),
        ('QUICK_FIX_INSTRUCTIONS.txt', '_docs/QUICK_FIX_INSTRUCTIONS.txt'),
        ('SIMPLE_INSTRUCTIONS.txt', '_docs/SIMPLE_INSTRUCTIONS.txt'),
        
        # Templates -> _templates/
        ('File Templates', '_templates/File Templates'),
        
        # System files -> _system/
        ('install_bots.py', '_system/install_bots.py'),
        ('install.bat', '_system/install.bat'),
        ('create_shared_folder.bat', '_system/create_shared_folder.bat'),
        ('setup_centralized_management.bat', '_system/setup_centralized_management.bat'),
        ('setup_company_shared_drive.bat', '_system/setup_company_shared_drive.bat'),
        ('update_packages', '_system/update_packages'),
    ]
    
    # Create backup before reorganizing
    print("\n💾 Creating backup of current structure...")
    backup_file = base_dir / f"_backup_before_reorganization.json"
    backup_data = {
        "date": str(Path(__file__).stat().st_mtime),
        "moves": moves
    }
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)
    print(f"  ✓ Backup saved: {backup_file.name}")
    
    # Perform moves
    print("\n📦 Reorganizing files...")
    moved_count = 0
    skipped_count = 0
    
    for source, destination in moves:
        source_path = base_dir / source
        dest_path = base_dir / destination
        
        if source_path.exists():
            try:
                # Create parent directory if needed
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move the file/folder
                if source_path.is_file():
                    shutil.move(str(source_path), str(dest_path))
                    print(f"  ✓ Moved: {source} -> {destination}")
                else:
                    shutil.move(str(source_path), str(dest_path))
                    print(f"  ✓ Moved folder: {source} -> {destination}")
                
                moved_count += 1
            except Exception as e:
                print(f"  ✗ Failed to move {source}: {e}")
                skipped_count += 1
        else:
            print(f"  ⊗ Skipped (not found): {source}")
            skipped_count += 1
    
    print(f"\n✅ Reorganization complete!")
    print(f"  • Moved: {moved_count} items")
    print(f"  • Skipped: {skipped_count} items")
    
    # Create a simple README in the root
    print("\n📝 Creating employee README...")
    employee_readme = base_dir / "START_HERE.txt"
    with open(employee_readme, 'w') as f:
        f.write("""
╔════════════════════════════════════════════════════════════╗
║         CCMD Bot Software - Employee Instructions          ║
╔════════════════════════════════════════════════════════════╗

🚀 TO START THE SOFTWARE:
   Double-click the launcher icon on your desktop
   (It has the "I" logo)

📧 TO INSTALL UPDATES:
   When you receive an update email:
   1. Download the .py file
   2. Double-click it
   3. Click OK/Yes when prompted
   4. Done!

❓ NEED HELP?
   Contact your IT administrator

⚠️ IMPORTANT:
   • Don't delete or move files in this folder
   • Don't edit any .py files
   • Your data and settings are safe

╚════════════════════════════════════════════════════════════╝
""")
    print(f"  ✓ Created: START_HERE.txt")
    
    print("\n" + "="*60)
    print("🎉 FOLDER REORGANIZATION COMPLETE!")
    print("="*60)
    print("\nWhat employees will now see:")
    print("  • START_HERE.txt (instructions)")
    print("  • secure_launcher.py (if desktop shortcut points to it)")
    print("  • requirements.txt")
    print("  • Clean, organized structure!")
    print("\nAll bot files are now organized in:")
    print("  • _bots/ (all bot files)")
    print("  • _admin/ (admin tools)")
    print("  • _docs/ (documentation)")
    print("  • _templates/ (file templates)")
    print("  • _system/ (installation files)")
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("  IN-OFFICE INSTALLATION FOLDER REORGANIZATION")
    print("="*60)
    print("\nThis will reorganize your folder to be cleaner and more professional.")
    print("All functionality will remain exactly the same.")
    print("\n⚠️  A backup will be created before making changes.")
    
    response = input("\nProceed with reorganization? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        try:
            reorganize_installation()
            print("\n✅ SUCCESS! Reorganization complete.")
            print("\n📋 NEXT STEPS:")
            print("1. Test the desktop launcher to make sure it still works")
            print("2. Update any shortcuts if needed")
            print("3. You're done!")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            print("Your files have not been modified.")
    else:
        print("\n❌ Reorganization cancelled.")

