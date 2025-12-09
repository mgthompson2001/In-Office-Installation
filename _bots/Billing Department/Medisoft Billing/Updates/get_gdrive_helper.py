"""
Helper script to find and configure G-Drive path.
Run this if you're not sure where your G-Drive is located.
"""

import os
from pathlib import Path

def find_gdrive_paths():
    """Find all possible G-Drive locations"""
    print("="*60)
    print("Finding G-Drive Locations")
    print("="*60)
    
    username = os.environ.get('USERNAME', '')
    
    # Check mapped drives (G:, H:, etc.)
    print("\n1. Checking mapped drives...")
    for drive_letter in 'GHIJKLMNOPQRSTUVWXYZ':
        drive_path = Path(f"{drive_letter}:\\")
        if drive_path.exists():
            # Check if it looks like Google Drive
            try:
                contents = list(drive_path.iterdir())
                if any('Google' in str(item) for item in contents) or any('Drive' in str(item) for item in contents):
                    print(f"   ✅ Found: {drive_path} (looks like Google Drive)")
                else:
                    print(f"   ⚠️  Found: {drive_path} (might be G-Drive)")
            except:
                pass
    
    # Check common Google Drive locations
    print("\n2. Checking common Google Drive locations...")
    common_paths = [
        Path(f"C:\\Users\\{username}\\Google Drive"),
        Path(f"C:\\Users\\{username}\\OneDrive\\Google Drive"),
        Path(f"C:\\Users\\{username}\\Desktop\\Google Drive"),
        Path(f"C:\\Users\\{username}\\Documents\\Google Drive"),
    ]
    
    for path in common_paths:
        if path.exists():
            print(f"   ✅ Found: {path}")
        else:
            print(f"   ❌ Not found: {path}")
    
    # Ask user
    print("\n" + "="*60)
    print("Which path is your company G-Drive?")
    print("="*60)
    print("\nEnter the full path, or press Enter to skip:")
    user_path = input("> ").strip()
    
    if user_path:
        test_path = Path(user_path)
        if test_path.exists():
            print(f"\n✅ Path exists: {test_path}")
            print(f"\nAdd this to config.json:")
            print(f'  "gdrive_path": "{user_path}"')
            return user_path
        else:
            print(f"\n❌ Path does not exist: {test_path}")
    else:
        print("\n⚠️  No path entered. Please edit config.json manually.")
    
    return None

if __name__ == "__main__":
    find_gdrive_paths()

