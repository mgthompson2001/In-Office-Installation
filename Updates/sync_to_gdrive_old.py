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
    """
    Try to find the G-Drive path automatically.
    Common locations:
    - G:\ (mapped drive)
    - C:\Users\[username]\Google Drive
    - C:\Users\[username]\OneDrive\Google Drive
    """
    # Try mapped G: drive first
    if Path("G:\\").exists():
        return Path("G:\\")
    
    # Try common Google Drive locations
    username = os.environ.get('USERNAME', '')
    common_paths = [
        Path(f"C:\\Users\\{username}\\Google Drive"),
        Path(f"C:\\Users\\{username}\\OneDrive\\Google Drive"),
        Path(f"C:\\Users\\{username}\\Desktop\\Google Drive"),
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

def sync_bot_to_gdrive(bot_config, master_folder, gdrive_updates_dir):
    """Sync a single bot to G-Drive"""
    bot_name = bot_config['name']
    source_path = bot_config.get('source_path', '')
    
    # Use master folder + source path
    source_dir = master_folder / source_path
    
    # Destination folder name (use bot name, sanitized)
    bot_folder_name = bot_name.replace(" ", "_")
    dest_dir = gdrive_updates_dir / bot_folder_name
    
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
        # Copy all files (excluding user data and temp files)
        exclude_patterns = [
            "__pycache__",
            "*.pyc",
            ".git",
            "_updates",
        ]
        
        # Add user data files to exclude
        user_data_files = bot_config.get('user_data_files', [])
        
        files_copied = 0
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(source_dir)
                relative_str = str(relative_path).replace("\\", "/")
                
                # Check if excluded
                excluded = False
                for pattern in exclude_patterns:
                    if pattern in relative_str or file_path.match(pattern):
                        excluded = True
                        break
                
                # Check user data files
                for user_file in user_data_files:
                    if user_file in relative_str or file_path.match(user_file):
                        excluded = True
                        break
                
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
    
    print(f"   ✅ Copied {files_copied} files")
    return True

def main():
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
    
    # Sync each bot
    success_count = 0
    for bot_config in config['bots']:
        if sync_bot_to_gdrive(bot_config, master_folder, gdrive_updates_dir):
            success_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Sync Complete!")
    print(f"{'='*60}")
    print(f"✅ Successfully synced: {success_count}/{len(config['bots'])} bots")
    print(f"\n📤 Updates are now available on G-Drive!")
    print(f"   Location: {gdrive_updates_dir}")
    print(f"\n💡 Employees will be prompted to update on next bot startup.")
    print(f"   Employees' bots should check: G:\\Company\\Software\\Updates\\")

if __name__ == "__main__":
    main()

