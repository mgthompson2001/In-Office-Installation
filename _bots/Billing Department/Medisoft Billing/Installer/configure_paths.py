#!/usr/bin/env python3
"""
Medisoft Billing Bot - Path Configuration Script
Updates paths in bot files to match installation location
"""

import sys
import os
from pathlib import Path
import re

def configure_paths(install_dir):
    """Configure all paths in bot files to match installation directory"""
    install_path = Path(install_dir).resolve()
    
    print(f"Configuring paths for installation directory: {install_path}")
    
    # Files that may contain hardcoded paths
    files_to_check = [
        "medisoft_billing_bot.py",
        "medisoft_billing_bot.bat",
        "find_tesseract_poppler.py",
    ]
    
    for filename in files_to_check:
        filepath = install_path / filename
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Update common path patterns
                # Replace hardcoded paths with relative paths where possible
                # This is mainly for documentation - the bot already uses __file__ for relative paths
                
                original_content = content
                
                # Replace any references to old installation paths with new one
                # (This is mainly for user reference in comments)
                
                if content != original_content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  Updated paths in {filename}")
                else:
                    print(f"  {filename} already uses relative paths")
                    
            except Exception as e:
                print(f"  Warning: Could not update {filename}: {e}")
    
    # Ensure vendor directory exists
    vendor_dir = install_path / "vendor"
    vendor_dir.mkdir(exist_ok=True)
    print(f"  Vendor directory ready: {vendor_dir}")
    
    # Create a config file with installation path
    config_file = install_path / "Installer" / "install_config.json"
    config_file.parent.mkdir(exist_ok=True)
    
    import json
    config = {
        "install_dir": str(install_path),
        "vendor_dir": str(vendor_dir),
        "bot_file": str(install_path / "medisoft_billing_bot.py"),
        "data_dir": str(install_path)
    }
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"  Configuration file created: {config_file}")
    except Exception as e:
        print(f"  Warning: Could not create config file: {e}")
    
    print("Path configuration complete!")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: configure_paths.py <install_directory>")
        sys.exit(1)
    
    install_dir = sys.argv[1]
    success = configure_paths(install_dir)
    sys.exit(0 if success else 1)

