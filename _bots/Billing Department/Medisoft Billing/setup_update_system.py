"""
Setup script for the auto-update system.
Run this once to set up version tracking and update manifests for all bots.
"""

import json
from pathlib import Path
from datetime import datetime
from update_manager import create_version_file, create_update_manifest

def setup_bot_update_system(bot_name: str, bot_directory: Path, version: str = "1.0.0", 
                           user_data_files: list = None, release_notes: str = ""):
    """
    Set up the update system for a single bot.
    
    Args:
        bot_name: Name of the bot
        bot_directory: Directory where bot is located
        version: Current version
        user_data_files: List of user data files to preserve
        release_notes: Release notes for this version
    """
    bot_path = Path(bot_directory)
    
    if not bot_path.exists():
        print(f"❌ Bot directory not found: {bot_path}")
        return False
    
    print(f"\n{'='*60}")
    print(f"Setting up update system for: {bot_name}")
    print(f"{'='*60}")
    
    # Create version file
    print(f"\n1. Creating version.json...")
    try:
        create_version_file(bot_path, version, bot_name, release_notes)
        print(f"   ✅ Version file created: {version}")
    except Exception as e:
        print(f"   ❌ Failed to create version file: {e}")
        return False
    
    # Create update manifest
    print(f"\n2. Creating update_manifest.json...")
    try:
        exclude_patterns = [
            "*.log",
            "__pycache__",
            "*.pyc",
            ".git",
            "_updates",
            "vendor",
        ]
        
        # Add user data files to exclude
        if user_data_files:
            exclude_patterns.extend(user_data_files)
        
        create_update_manifest(bot_path, exclude_patterns=exclude_patterns)
        print(f"   ✅ Update manifest created")
    except Exception as e:
        print(f"   ❌ Failed to create manifest: {e}")
        return False
    
    print(f"\n✅ Update system setup complete for {bot_name}!")
    return True


def setup_all_bots(base_directory: Path):
    """
    Set up update system for all bots in the directory structure.
    
    Args:
        base_directory: Base directory containing all bots
    """
    base_path = Path(base_directory)
    
    print("="*60)
    print("Auto-Update System Setup")
    print("="*60)
    print(f"\nBase directory: {base_path}")
    
    # Define all bots
    bots = [
        {
            'name': 'Medisoft Billing Bot',
            'path': base_path / '_bots' / 'Billing Department' / 'Medisoft Billing',
            'version': '1.0.0',
            'user_data_files': [
                'medisoft_users.json',
                'medisoft_coordinates.json',
                '*.png'  # Saved selector images
            ],
            'release_notes': 'Initial release with auto-update support'
        },
        {
            'name': 'Missed Appointments Tracker Bot',
            'path': base_path / '_bots' / 'Billing Department' / 'Medisoft Billing' / 'Missed Appointments Tracker Bot',
            'version': '1.0.0',
            'user_data_files': [
                'missed_appointments_tracker_users.json',
                'email_configs.json',
                'missed_appointments_tracker.log'
            ],
            'release_notes': 'Initial release with auto-update support'
        },
        {
            'name': 'Real Estate Financial Tracker',
            'path': base_path / '_bots' / 'Billing Department' / 'Medisoft Billing' / 'Real Estate Financial Tracker',
            'version': '1.0.0',
            'user_data_files': [
                '*.json',  # All JSON files are user data
                '*.log'
            ],
            'release_notes': 'Initial release with auto-update support'
        },
    ]
    
    # Check if base directory exists
    if not base_path.exists():
        print(f"\n❌ Base directory not found: {base_path}")
        print(f"   Please update the path in this script.")
        return
    
    # Setup each bot
    success_count = 0
    for bot in bots:
        if bot['path'].exists():
            if setup_bot_update_system(
                bot_name=bot['name'],
                bot_directory=bot['path'],
                version=bot['version'],
                user_data_files=bot['user_data_files'],
                release_notes=bot['release_notes']
            ):
                success_count += 1
        else:
            print(f"\n⚠️  Bot directory not found: {bot['path']}")
            print(f"   Skipping {bot['name']}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Setup Complete!")
    print(f"{'='*60}")
    print(f"✅ Successfully set up: {success_count}/{len(bots)} bots")
    print(f"\nNext steps:")
    print(f"1. Review the version.json files created for each bot")
    print(f"2. Add update checking code to each bot (see UPDATE_SYSTEM_SETUP_GUIDE.md)")
    print(f"3. Test the update system on one computer")
    print(f"4. Deploy to all users")


if __name__ == "__main__":
    import sys
    
    # Default base directory (your OneDrive location)
    default_base = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")
    
    if len(sys.argv) > 1:
        base_directory = Path(sys.argv[1])
    else:
        base_directory = default_base
    
    # Check if default exists, if not, ask user
    if not base_directory.exists():
        print("="*60)
        print("Auto-Update System Setup")
        print("="*60)
        print(f"\nDefault directory not found: {base_directory}")
        print(f"\nPlease provide the path to your bot installation directory.")
        print(f"Example: C:\\Users\\YourName\\OneDrive\\Desktop\\In-Office Installation")
        
        user_path = input("\nEnter path (or press Enter to use default): ").strip()
        if user_path:
            base_directory = Path(user_path)
        else:
            base_directory = default_base
    
    setup_all_bots(base_directory)

