"""
Release Update Script
Run this script when you want to release a new version of your bots.
This will update version numbers and regenerate update manifests.
"""

import json
from pathlib import Path
from datetime import datetime
from update_manager import create_version_file, create_update_manifest
import sys

def release_bot_update(bot_name: str, bot_directory: Path, new_version: str, 
                      release_notes: str = "", user_data_files: list = None):
    """
    Release a new version of a bot.
    
    Args:
        bot_name: Name of the bot
        bot_directory: Directory where bot is located
        new_version: New version number (e.g., "1.0.1")
        release_notes: Release notes for this version
        user_data_files: List of user data files to preserve
    """
    bot_path = Path(bot_directory)
    
    if not bot_path.exists():
        print(f"❌ Bot directory not found: {bot_path}")
        return False
    
    print(f"\n{'='*60}")
    print(f"Releasing update for: {bot_name}")
    print(f"{'='*60}")
    
    # Read current version
    version_file = bot_path / "version.json"
    current_version = "0.0.0"
    if version_file.exists():
        try:
            with open(version_file, 'r') as f:
                version_data = json.load(f)
                current_version = version_data.get('version', '0.0.0')
        except:
            pass
    
    print(f"Current version: {current_version}")
    print(f"New version: {new_version}")
    
    if not release_notes:
        release_notes = input(f"\nEnter release notes for {new_version}: ").strip()
        if not release_notes:
            release_notes = f"Update to version {new_version}"
    
    # Update version file
    print(f"\n1. Updating version.json...")
    try:
        create_version_file(bot_path, new_version, bot_name, release_notes)
        print(f"   ✅ Version updated to {new_version}")
    except Exception as e:
        print(f"   ❌ Failed to update version: {e}")
        return False
    
    # Regenerate update manifest
    print(f"\n2. Regenerating update_manifest.json...")
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
        print(f"   ✅ Update manifest regenerated")
    except Exception as e:
        print(f"   ❌ Failed to regenerate manifest: {e}")
        return False
    
    print(f"\n✅ Update released successfully!")
    print(f"\nNext steps:")
    print(f"1. Wait for OneDrive/SharePoint to sync")
    print(f"2. Users will be prompted to update on next bot startup")
    print(f"3. Test the update on one computer first")
    
    return True


def release_all_bots_update(base_directory: Path, new_version: str, release_notes: str = ""):
    """
    Release updates for all bots at once.
    
    Args:
        base_directory: Base directory containing all bots
        new_version: New version number for all bots
        release_notes: Release notes (same for all bots)
    """
    base_path = Path(base_directory)
    
    print("="*60)
    print("Release Update for All Bots")
    print("="*60)
    print(f"\nBase directory: {base_path}")
    print(f"New version: {new_version}")
    
    # Define all bots
    bots = [
        {
            'name': 'Medisoft Billing Bot',
            'path': base_path / '_bots' / 'Billing Department' / 'Medisoft Billing',
            'user_data_files': [
                'medisoft_users.json',
                'medisoft_coordinates.json',
                '*.png'
            ]
        },
        {
            'name': 'Missed Appointments Tracker Bot',
            'path': base_path / '_bots' / 'Billing Department' / 'Medisoft Billing' / 'Missed Appointments Tracker Bot',
            'user_data_files': [
                'missed_appointments_tracker_users.json',
                'email_configs.json',
                'missed_appointments_tracker.log'
            ]
        },
        {
            'name': 'Real Estate Financial Tracker',
            'path': base_path / '_bots' / 'Billing Department' / 'Medisoft Billing' / 'Real Estate Financial Tracker',
            'user_data_files': [
                '*.json',
                '*.log'
            ]
        },
    ]
    
    if not release_notes:
        release_notes = input(f"\nEnter release notes for version {new_version}: ").strip()
        if not release_notes:
            release_notes = f"Update to version {new_version}"
    
    # Release update for each bot
    success_count = 0
    for bot in bots:
        if bot['path'].exists():
            if release_bot_update(
                bot_name=bot['name'],
                bot_directory=bot['path'],
                new_version=new_version,
                release_notes=release_notes,
                user_data_files=bot['user_data_files']
            ):
                success_count += 1
        else:
            print(f"\n⚠️  Bot directory not found: {bot['path']}")
            print(f"   Skipping {bot['name']}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Release Complete!")
    print(f"{'='*60}")
    print(f"✅ Successfully released: {success_count}/{len(bots)} bots")
    print(f"\nVersion {new_version} is now available for update!")


if __name__ == "__main__":
    import sys
    
    # Default base directory
    default_base = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")
    
    if len(sys.argv) < 2:
        print("="*60)
        print("Release Update Script")
        print("="*60)
        print("\nUsage:")
        print("  python release_update.py <new_version> [release_notes]")
        print("\nExample:")
        print("  python release_update.py 1.0.1 \"Fixed login bug\"")
        print("\nOr run interactively:")
        print("  python release_update.py")
        print()
        
        new_version = input("Enter new version number (e.g., 1.0.1): ").strip()
        if not new_version:
            print("❌ Version number required")
            sys.exit(1)
        
        release_notes = input("Enter release notes (optional): ").strip()
        
        base_directory = default_base
        if not base_directory.exists():
            user_path = input(f"\nEnter bot directory path (default: {default_base}): ").strip()
            if user_path:
                base_directory = Path(user_path)
    else:
        new_version = sys.argv[1]
        release_notes = sys.argv[2] if len(sys.argv) > 2 else ""
        base_directory = default_base
    
    release_all_bots_update(base_directory, new_version, release_notes)

