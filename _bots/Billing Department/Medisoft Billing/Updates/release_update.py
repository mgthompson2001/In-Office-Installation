"""
Release Update for All Bots
Run this when you want to release a new version of all bots.
This updates version numbers and regenerates manifests.
"""

import json
from pathlib import Path
from datetime import datetime
import sys

# Import update_manager from same directory
sys.path.insert(0, str(Path(__file__).parent))
from update_manager import create_version_file, create_update_manifest

def release_all_bots(new_version: str, release_notes: str = ""):
    """Release a new version for all bots"""
    updates_dir = Path(__file__).parent
    config_file = updates_dir / "config.json"
    
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    print("="*60)
    print(f"Releasing Version {new_version}")
    print("="*60)
    
    if not release_notes:
        release_notes = input(f"\nEnter release notes for version {new_version}: ").strip()
        if not release_notes:
            release_notes = f"Update to version {new_version}"
    
    # Get master folder
    master_folder_str = config.get('master_folder', '')
    if not master_folder_str:
        print("❌ 'master_folder' not set in config.json")
        return
    
    master_folder = Path(master_folder_str)
    if not master_folder.exists():
        print(f"❌ Master folder does not exist: {master_folder}")
        return
    
    success_count = 0
    for bot_config in config['bots']:
        bot_name = bot_config['name']
        source_path = bot_config.get('source_path', '')
        user_data_files = bot_config.get('user_data_files', [])
        
        bot_dir = master_folder / source_path
        
        if not bot_dir.exists():
            print(f"\n⚠️  Bot directory not found: {bot_dir}")
            continue
        
        print(f"\n📦 Releasing {bot_name}...")
        
        # Update version file
        try:
            create_version_file(
                bot_directory=bot_dir,
                version=new_version,
                bot_name=bot_name,
                release_notes=release_notes
            )
            print(f"   ✅ Updated version.json to {new_version}")
        except Exception as e:
            print(f"   ❌ Failed to update version: {e}")
            continue
        
        # Regenerate manifest
        try:
            # Only exclude system/temp files and user data files
            # Everything else (install.bat, requirements.txt, .ps1, etc.) will be included
            exclude_patterns = [
                "__pycache__",
                "*.pyc",
                ".git",
                "_updates",
            ]
            # Add user data files to exclude (saved logins, settings, coordinates, logs, etc.)
            # These are the ONLY files that won't be updated - everything else gets updated
            exclude_patterns.extend(user_data_files)
            
            # Include ALL files (not just specific types) - pass None for files_to_include
            # This ensures install.bat, requirements.txt, .ps1, and all other files are updated
            create_update_manifest(
                bot_directory=bot_dir,
                files_to_include=None,  # None = include ALL files
                exclude_patterns=exclude_patterns
            )
            print(f"   ✅ Regenerated update_manifest.json")
            success_count += 1
        except Exception as e:
            print(f"   ❌ Failed to regenerate manifest: {e}")
    
    # Update config.json with new version
    for bot_config in config['bots']:
        bot_config['version'] = new_version
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Release Complete!")
    print(f"{'='*60}")
    print(f"✅ Successfully released: {success_count}/{len(config['bots'])} bots")
    print(f"\nNext step: Run sync_to_gdrive.py to push updates to G-Drive")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python release_update.py <new_version> [release_notes]")
        print("Example: python release_update.py 1.0.1 \"Fixed login bug\"")
        new_version = input("\nEnter new version number: ").strip()
        if not new_version:
            print("❌ Version number required")
            sys.exit(1)
        release_notes = input("Enter release notes (optional): ").strip()
    else:
        new_version = sys.argv[1]
        release_notes = sys.argv[2] if len(sys.argv) > 2 else ""
    
    release_all_bots(new_version, release_notes)

