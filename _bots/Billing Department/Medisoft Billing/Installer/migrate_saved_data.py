#!/usr/bin/env python3
"""
Medisoft Billing Bot - Data Migration Script
Migrates saved selectors, coordinates, and user data from old installations
"""

import sys
import os
import json
import shutil
from pathlib import Path

def migrate_saved_data(install_dir):
    """Migrate saved data files to new installation"""
    install_path = Path(install_dir).resolve()
    
    print(f"Migrating saved data to: {install_path}")
    
    # Files to migrate
    data_files = [
        "medisoft_coordinates.json",
        "medisoft_users.json",
        "therapy_notes_records_settings.json",
        "therapy_notes_records_users.json",
        "tn_coordinates.json",
        "tn_users.json",
    ]
    
    # Common locations to check for old data
    search_locations = [
        Path.home() / "Desktop" / "Medisoft Billing",
        Path.home() / "Documents" / "Medisoft Billing",
        Path.home() / "Downloads" / "Medisoft Billing",
        Path("C:/Program Files/Medisoft Billing"),
        Path("C:/Program Files (x86)/Medisoft Billing"),
    ]
    
    migrated_count = 0
    
    for old_location in search_locations:
        if not old_location.exists():
            continue
            
        print(f"  Checking: {old_location}")
        
        for data_file in data_files:
            old_file = old_location / data_file
            new_file = install_path / data_file
            
            if old_file.exists() and old_file != new_file:
                try:
                    # If new file already exists, merge data
                    if new_file.exists():
                        print(f"    Merging {data_file}...")
                        
                        # Try to merge JSON files
                        try:
                            with open(old_file, 'r') as f:
                                old_data = json.load(f)
                            with open(new_file, 'r') as f:
                                new_data = json.load(f)
                            
                            # Merge dictionaries (new takes precedence)
                            if isinstance(old_data, dict) and isinstance(new_data, dict):
                                merged = {**old_data, **new_data}
                                with open(new_file, 'w') as f:
                                    json.dump(merged, f, indent=2)
                                print(f"      ✓ Merged {data_file}")
                                migrated_count += 1
                        except json.JSONDecodeError:
                            # Not JSON, skip merging
                            print(f"      ⚠ Could not merge {data_file} (invalid JSON)")
                            
                    else:
                        # Copy file
                        shutil.copy2(old_file, new_file)
                        print(f"      ✓ Copied {data_file}")
                        migrated_count += 1
                        
                except Exception as e:
                    print(f"      ✗ Could not migrate {data_file}: {e}")
    
    # Also check for PNG image files (saved selectors)
    image_files = list(install_path.glob("*.png"))
    if image_files:
        print(f"  Found {len(image_files)} image files in installation directory")
    
    # Check for images in old locations
    for old_location in search_locations:
        if not old_location.exists():
            continue
        old_images = list(old_location.glob("*.png"))
        for old_image in old_images:
            new_image = install_path / old_image.name
            if not new_image.exists():
                try:
                    shutil.copy2(old_image, new_image)
                    print(f"    ✓ Copied image: {old_image.name}")
                    migrated_count += 1
                except Exception as e:
                    print(f"    ✗ Could not copy {old_image.name}: {e}")
    
    if migrated_count > 0:
        print(f"\n✓ Migration complete! Migrated {migrated_count} file(s)")
    else:
        print("\n  No data files found to migrate (this is normal for new installations)")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: migrate_saved_data.py <install_directory>")
        sys.exit(1)
    
    install_dir = sys.argv[1]
    success = migrate_saved_data(install_dir)
    sys.exit(0 if success else 1)

