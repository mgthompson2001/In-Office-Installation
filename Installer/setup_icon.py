#!/usr/bin/env python3
"""
Medisoft Billing Bot - Icon Setup Script
Copies and converts the red I icon for desktop shortcut
"""

import sys
import os
import shutil
from pathlib import Path

def setup_icon(install_dir):
    """Set up the icon file for desktop shortcut"""
    install_path = Path(install_dir).resolve()
    installer_path = install_path / "Installer"
    
    # Look for the icon in various locations
    icon_sources = [
        # From _admin directory (relative to In-Office Installation)
        install_path / ".." / ".." / ".." / "_admin" / "ccmd_bot_icon.png",
        # Absolute path check
        Path("C:/Users") / os.getenv("USERNAME", "mthompson") / "OneDrive - Integrity Senior Services" / "Desktop" / "In-Office Installation" / "_admin" / "ccmd_bot_icon.png",
        # Check if already in installer directory
        installer_path / "ccmd_bot_icon.png",
        installer_path / "medisoft_bot_icon.ico",
        installer_path / "icon.ico",
    ]
    
    # Target icon location
    target_icon = installer_path / "medisoft_bot_icon.ico"
    
    # Try to find and copy the icon
    for icon_source in icon_sources:
        if icon_source.exists():
            try:
                # If it's a PNG, we'll use it directly (VBScript can handle PNG in newer Windows)
                # But we'll also copy it for reference
                if icon_source.suffix.lower() == '.png':
                    # Copy PNG
                    png_target = installer_path / "medisoft_bot_icon.png"
                    shutil.copy2(icon_source, png_target)
                    print(f"  ✓ Copied icon: {icon_source.name} -> {png_target.name}")
                    
                    # Try to convert to ICO if PIL is available
                    try:
                        from PIL import Image
                        img = Image.open(icon_source)
                        # Convert to ICO format
                        img.save(target_icon, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
                        print(f"  ✓ Created ICO icon: {target_icon.name}")
                        return str(target_icon)
                    except ImportError:
                        print(f"  ⚠ PIL not available, using PNG directly")
                        return str(png_target)
                    except Exception as e:
                        print(f"  ⚠ Could not convert to ICO: {e}, using PNG")
                        return str(png_target)
                
                elif icon_source.suffix.lower() == '.ico':
                    # Already an ICO, just copy it
                    shutil.copy2(icon_source, target_icon)
                    print(f"  ✓ Copied ICO icon: {icon_source.name} -> {target_icon.name}")
                    return str(target_icon)
                    
            except Exception as e:
                print(f"  ✗ Could not copy icon from {icon_source}: {e}")
                continue
    
    # If no icon found, create a fallback
    print("  ⚠ Icon file not found - shortcut will use default icon")
    print("    You can add medisoft_bot_icon.ico or medisoft_bot_icon.png to the Installer folder")
    
    # Create a simple text file with instructions
    readme_path = installer_path / "ICON_README.txt"
    with open(readme_path, 'w') as f:
        f.write("Icon Setup Instructions\n")
        f.write("=======================\n\n")
        f.write("To set a custom icon for the desktop shortcut:\n\n")
        f.write("1. Place an icon file named 'medisoft_bot_icon.ico' or 'medisoft_bot_icon.png'\n")
        f.write("   in this Installer folder.\n\n")
        f.write("2. The icon should be a square image (recommended: 256x256 pixels).\n\n")
        f.write("3. Run the installer again or manually update the desktop shortcut.\n\n")
        f.write("Note: The installer will look for the red I icon at:\n")
        f.write("  _admin/ccmd_bot_icon.png\n\n")
    
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: setup_icon.py <install_directory>")
        sys.exit(1)
    
    install_dir = sys.argv[1]
    icon_path = setup_icon(install_dir)
    
    if icon_path:
        print(f"\n✓ Icon setup complete: {icon_path}")
        sys.exit(0)
    else:
        print("\n⚠ Icon setup incomplete - shortcut may use default icon")
        sys.exit(0)  # Not a critical error

