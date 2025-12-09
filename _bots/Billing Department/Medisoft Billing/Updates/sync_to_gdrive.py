"""
Sync Updates to G-Drive
This script copies updates from your local Updates folder to the company G-Drive.
Run this whenever you want to push updates to employees.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
import os

def find_gdrive_path():
    """Try to find the G-Drive path automatically"""
    # Try mapped G: drive first
    if Path(r"G:\").exists():
        return Path(r"G:\")
    
    # Try common Google Drive locations
    username = os.environ.get('USERNAME', '')
    common_paths = [
        Path(fr"C:\Users\{username}\Google Drive"),
        Path(fr"C:\Users\{username}\OneDrive\Google Drive"),
        Path(fr"C:\Users\{username}\Desktop\Google Drive"),
    ]
    
    for path in common_paths:
        if path.exists():
            return path
    
    return None

def load_config():
    """Load configuration from config.json"""
    config_file = Path(__file__).parent / "config.json"
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return None
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # If G-Drive path not set, try to find it
    if not config.get('gdrive_path') or not Path(config['gdrive_path']).exists():
        gdrive = find_gdrive_path()
        if gdrive:
            config['gdrive_path'] = str(gdrive)
            print(f"✅ Found G-Drive at: {gdrive}")
        else:
            print("❌ Could not find G-Drive automatically")
            print("   Please edit config.json and set 'gdrive_path' manually")
            return None
    
    return config

def sync_entire_folder(master_folder, version_folder, user_data_patterns):
    """Sync entire master folder to version folder, excluding user data"""
    from fnmatch import fnmatch
    
    # Exclude patterns (system/temp files)
    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        ".git",
        "_updates",
    ]
    
    files_copied = 0
    
    # Walk through entire master folder
    for file_path in master_folder.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(master_folder)
            relative_str = str(relative_path).replace("\\", "/")
            
            # Skip the Updates folder itself (master control center - don't sync this)
            if relative_str.startswith("Updates/"):
                continue
            
            # Check if excluded (system/temp files)
            excluded = False
            for pattern in exclude_patterns:
                if fnmatch(relative_str, pattern) or fnmatch(file_path.name, pattern) or pattern in relative_str:
                    excluded = True
                    break
            
            # Check user data files (preserve employee's saved data)
            if not excluded:
                for user_pattern in user_data_patterns:
                    if fnmatch(relative_str, user_pattern) or fnmatch(file_path.name, user_pattern):
                        excluded = True
                        break
            
            # Copy file if not excluded
            if not excluded:
                dest_file = version_folder / relative_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_file)
                files_copied += 1
    
    print(f"   ✅ Copied {files_copied} files")
    return files_copied

def sync_bot_to_gdrive_old(bot_config, master_folder, version_folder):
    """Sync a single bot to G-Drive version folder"""
    bot_name = bot_config['name']
    source_path = bot_config.get('source_path', '')
    
    # Use master folder + source path
    source_dir = master_folder / source_path
    
    # Destination folder name (use bot name, sanitized)
    # Put bot folder inside the version folder
    bot_folder_name = bot_name.replace(" ", "_")
    dest_dir = version_folder / bot_folder_name
    
    if not source_dir.exists():
        print(f"⚠️  Source directory not found: {source_dir}")
        return False
    
    print(f"\n📦 Syncing {bot_name}...")
    print(f"   From: {source_dir}")
    print(f"   To: {dest_dir}")
    
    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we should only include specific files (for Therapy Notes bot)
    include_files = bot_config.get('include_files', None)
    
    if include_files:
        # Only copy specific files
        files_copied = 0
        for pattern in include_files:
            for file_path in source_dir.glob(pattern):
                if file_path.is_file():
                    relative_path = file_path.relative_to(source_dir)
                    dest_file = dest_dir / relative_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest_file)
                    files_copied += 1
    else:
        # Copy ALL files (excluding ONLY user data and temp files)
        # This includes: .py, .bat, .txt, .md, .ps1, .exe, .dll, requirements.txt, etc.
        # ONLY user data files (saved logins, settings, coordinates) are excluded
        from fnmatch import fnmatch
        
        # Only exclude system/temp files
        exclude_patterns = [
            "__pycache__",
            "*.pyc",
            ".git",
            "_updates",
        ]
        
        # Add user data files to exclude (saved logins, settings, coordinates, etc.)
        # These are the ONLY files that won't be updated
        user_data_files = bot_config.get('user_data_files', [])
        
        files_copied = 0
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(source_dir)
                relative_str = str(relative_path).replace("\\", "/")
                
                # Check if excluded (use fnmatch for proper wildcard matching)
                excluded = False
                for pattern in exclude_patterns:
                    if fnmatch(relative_str, pattern) or fnmatch(file_path.name, pattern) or pattern in relative_str:
                        excluded = True
                        break
                
                # Check user data files (use fnmatch for wildcard patterns like *.json)
                if not excluded:
                    for user_file in user_data_files:
                        if fnmatch(relative_str, user_file) or fnmatch(file_path.name, user_file) or user_file in relative_str:
                            excluded = True
                            break
                
                # Copy ALL files that aren't excluded
                if not excluded:
                    dest_file = dest_dir / relative_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest_file)
                    files_copied += 1
    
    # Copy version.json if it exists
    version_file = source_dir / "version.json"
    if version_file.exists():
        shutil.copy2(version_file, dest_dir / "version.json")
        print(f"   ✅ Copied version.json")
    
    # Copy update_manifest.json if it exists
    manifest_file = source_dir / "update_manifest.json"
    if manifest_file.exists():
        shutil.copy2(manifest_file, dest_dir / "update_manifest.json")
        print(f"   ✅ Copied update_manifest.json")
    
    # Add timestamp to bot files before copying
    print(f"   📅 Adding update timestamp to bot files...")
    try:
        from add_timestamp_helper import add_timestamp_to_bot_file
        timestamp = datetime.now().strftime("%m/%d/%Y")
        # Find main bot Python files
        for py_file in source_dir.glob("*bot*.py"):
            if py_file.is_file() and "update" not in py_file.name.lower():
                if add_timestamp_to_bot_file(py_file, timestamp):
                    print(f"      ✅ Added timestamp to {py_file.name}")
    except Exception as e:
        print(f"   ⚠️  Could not add timestamps: {e}")
    
    print(f"   ✅ Copied {files_copied} files")
    return True

def main(version_override=None):
    """Main sync function"""
    print("="*60)
    print("Sync Updates to G-Drive")
    print("="*60)
    
    # Load config
    config = load_config()
    if not config:
        return
    
    # Get master folder path
    master_folder_str = config.get('master_folder', '')
    if not master_folder_str:
        print("❌ 'master_folder' not set in config.json")
        print("   Please set it to your In-Office Installation path")
        return
    
    master_folder = Path(master_folder_str)
    if not master_folder.exists():
        print(f"❌ Master folder does not exist: {master_folder}")
        print("   Please check config.json and set the correct master_folder path")
        return
    
    gdrive_path = Path(config['gdrive_path'])
    gdrive_updates_folder = config.get('gdrive_updates_folder', 'Bot Updates')
    gdrive_updates_dir = gdrive_path / gdrive_updates_folder
    
    print(f"\n📁 Master folder: {master_folder}")
    print(f"📁 G-Drive path: {gdrive_path}")
    print(f"📁 G-Drive updates folder: {gdrive_updates_dir}")
    
    if not gdrive_path.exists():
        print(f"\n❌ G-Drive path does not exist: {gdrive_path}")
        print("   Please check config.json and set the correct G-Drive path")
        return
    
    # Create G-Drive updates folder if it doesn't exist
    gdrive_updates_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean up old bot folders from root (leftover from old sync method)
    print(f"\n🧹 Cleaning up old bot folders from root...")
    old_bot_folders = []
    for item in gdrive_updates_dir.iterdir():
        if item.is_dir():
            # Check if it's a bot folder (not a version folder, not __pycache__)
            import re
            is_version_folder = re.match(r'^\d+\.\d+(\.\d+)?$', item.name)
            if not is_version_folder and item.name not in ["__pycache__"]:
                # Check if it looks like a bot folder (has version.json inside)
                if (item / "version.json").exists():
                    old_bot_folders.append(item)
    
    for old_folder in old_bot_folders:
        print(f"   🗑️  Removing old folder: {old_folder.name}")
        import shutil
        try:
            shutil.rmtree(old_folder)
        except Exception as e:
            print(f"   ⚠️  Could not remove {old_folder.name}: {e}")
    
    # Get version number
    version = version_override  # Use override if provided
    if not version:
        # Read from first bot's version.json (all bots should have same version after release_update.py)
        version = "1.0.0"  # Default
        if config['bots']:
            first_bot = config['bots'][0]
            source_path = first_bot.get('source_path', '')
            bot_dir = master_folder / source_path
            version_file = bot_dir / "version.json"
            if version_file.exists():
                try:
                    with open(version_file, 'r') as f:
                        version_data = json.load(f)
                        version = version_data.get('version', '1.0.0')
                except Exception as e:
                    print(f"⚠️  Could not read version file: {e}")
    
    print(f"\n📦 Version: {version}")
    
    # Create version folder (e.g., "1.1/") - THIS IS WHERE ALL FILES GO
    version_folder = gdrive_updates_dir / version
    if version_folder.exists():
        print(f"⚠️  Version folder already exists: {version_folder}")
        print(f"   Removing old version folder to replace with new update...")
        import shutil
        try:
            shutil.rmtree(version_folder)
        except Exception as e:
            print(f"   ⚠️  Could not remove old version folder: {e}")
            print(f"   Please manually delete: {version_folder}")
            return
    
    version_folder.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created version folder: {version_folder.name}")
    print(f"   Full path: {version_folder}")
    
    # Sync ENTIRE master folder structure to version folder
    print(f"\n📦 Syncing entire In-Office Installation folder...")
    print(f"   From: {master_folder}")
    print(f"   To: {version_folder}")
    
    # Collect all user data file patterns from all bots
    all_user_data_patterns = set()
    for bot_config in config.get('bots', []):
        for pattern in bot_config.get('user_data_files', []):
            all_user_data_patterns.add(pattern)
    
    # Sync entire folder structure
    files_copied = sync_entire_folder(master_folder, version_folder, all_user_data_patterns)
    
    success_count = len(config.get('bots', [])) if files_copied > 0 else 0
    
    # Copy update bot files to G-Drive root (employees see these)
    print(f"\n📦 Copying Update Bot to G-Drive root...")
    try:
        updates_dir = master_folder / "Updates"
        update_bot_files = ["update_bot.py", "update_bot.bat", "update_manager.py", "add_timestamp_helper.py"]
        
        for file_name in update_bot_files:
            source_file = updates_dir / file_name
            if source_file.exists():
                dest_file = gdrive_updates_dir / file_name
                shutil.copy2(source_file, dest_file)
                print(f"   ✅ Copied {file_name}")
        
        # Also copy config.json to root so update bot can read user_data_files
        config_file = updates_dir / "config.json"
        if config_file.exists():
            dest_config = gdrive_updates_dir / "config.json"
            shutil.copy2(config_file, dest_config)
            print(f"   ✅ Copied config.json")
        
        print(f"   ✅ Update bot files copied to G-Drive root")
    except Exception as e:
        print(f"   ⚠️  Could not copy update bot files: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ UPDATE SUCCESSFULLY PUSHED TO G-DRIVE!")
    print(f"{'='*60}")
    print(f"\n✅ Successfully synced entire In-Office Installation folder")
    print(f"   Files copied: {files_copied}")
    print(f"   Version: {version}")
    print(f"\n📤 Updates are now available on G-Drive!")
    print(f"   Root folder: {gdrive_updates_dir}")
    print(f"   Version folder: {version_folder}")
    print(f"\n📁 Folder Structure:")
    print(f"   {gdrive_updates_dir.name}/")
    print(f"   ├── update_bot.bat          (employees run this)")
    print(f"   ├── update_bot.py")
    print(f"   ├── update_manager.py")
    print(f"   ├── config.json")
    print(f"   └── {version}/              ← ALL UPDATES ARE HERE")
    print(f"       ├── _bots/")
    print(f"       ├── _admin/")
    print(f"       ├── _docs/")
    print(f"       ├── AI/")
    print(f"       └── ... (entire folder structure)")
    print(f"\n💡 Employees should run 'update_bot.bat' from G-Drive to update their software")
    print(f"\n📍 Update location: {version_folder}")

if __name__ == "__main__":
    import sys
    version_arg = None
    if len(sys.argv) > 1:
        version_arg = sys.argv[1]
    main(version_override=version_arg)
