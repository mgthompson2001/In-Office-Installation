"""
Setup all bots in the Updates folder for the update system.
This creates version.json and update_manifest.json for each bot.
"""

import json
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path to import update_manager
sys.path.insert(0, str(Path(__file__).parent.parent))
from update_manager import create_version_file, create_update_manifest

def setup_all_bots():
    """Set up version tracking for all bots"""
    updates_dir = Path(__file__).parent
    config_file = updates_dir / "config.json"
    
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    print("="*60)
    print("Setting Up All Bots for Updates")
    print("="*60)
    
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
        version = bot_config.get('version', '1.0.0')
        user_data_files = bot_config.get('user_data_files', [])
        
        bot_dir = master_folder / source_path
        
        if not bot_dir.exists():
            print(f"\n⚠️  Bot directory not found: {bot_dir}")
            print(f"   Skipping {bot_name}")
            continue
        
        print(f"\n{'='*60}")
        print(f"Setting up: {bot_name}")
        print(f"{'='*60}")
        
        # Create version file
        try:
            create_version_file(
                bot_directory=bot_dir,
                version=version,
                bot_name=bot_name,
                release_notes=f"Initial setup - version {version}"
            )
            print(f"✅ Created version.json")
        except Exception as e:
            print(f"❌ Failed to create version.json: {e}")
            continue
        
        # Create update manifest
        try:
            exclude_patterns = [
                "__pycache__",
                "*.pyc",
                ".git",
                "_updates",
                "*.log",
            ]
            exclude_patterns.extend(user_data_files)
            
            create_update_manifest(
                bot_directory=bot_dir,
                exclude_patterns=exclude_patterns
            )
            print(f"✅ Created update_manifest.json")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to create manifest: {e}")
    
    print(f"\n{'='*60}")
    print(f"Setup Complete!")
    print(f"{'='*60}")
    print(f"✅ Successfully set up: {success_count}/{len(config['bots'])} bots")
    print(f"\nNext steps:")
    print(f"1. Copy your bot files to Updates/bots/[Bot Name]/")
    print(f"2. Run sync_to_gdrive.py to push updates to G-Drive")

if __name__ == "__main__":
    setup_all_bots()

