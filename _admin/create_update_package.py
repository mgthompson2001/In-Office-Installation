#!/usr/bin/env python3
"""
Create Update Package - Generates update packages for deployment
This tool creates update packages that can be deployed across all employee computers.
"""

import os
import sys
import json
import zipfile
import hashlib
from pathlib import Path
import argparse
from datetime import datetime
import shutil

class UpdatePackageCreator:
    def __init__(self):
        self.package_dir = Path("update_packages")
        self.package_dir.mkdir(exist_ok=True)
        
    def create_package(self, version, changes, source_dir=".", output_dir=None):
        """Create an update package"""
        if output_dir is None:
            output_dir = self.package_dir
        
        print(f"Creating update package for version {version}...")
        
        # Create package directory
        package_name = f"ccmd_bots_v{version}"
        package_path = Path(output_dir) / package_name
        package_path.mkdir(exist_ok=True)
        
        # Copy bot files
        self._copy_bot_files(source_dir, package_path)
        
        # Create version.json
        self._create_version_file(package_path, version, changes)
        
        # Create update script
        self._create_update_script(package_path)
        
        # Create checksums
        self._create_checksums(package_path)
        
        # Create zip package
        zip_path = self._create_zip_package(package_path, output_dir)
        
        print(f"✅ Update package created: {zip_path}")
        return zip_path
    
    def _copy_bot_files(self, source_dir, package_path):
        """Copy bot files to package directory"""
        print("Copying bot files...")
        
        source = Path(source_dir)
        bot_files = [
            "Launcher",
            "Referral bot and bridge (final)",
            "The Welcomed One, Exalted Rank",
            "Med Rec",
            "Cursor versions",
            "File Templates",
            "secure_launcher.py",
            "requirements.txt"
        ]
        
        for item in bot_files:
            source_path = source / item
            if source_path.exists():
                dest_path = package_path / item
                if source_path.is_file():
                    shutil.copy2(source_path, dest_path)
                elif source_path.is_dir():
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                print(f"  ✅ Copied: {item}")
            else:
                print(f"  ⚠️  Not found: {item}")
    
    def _create_version_file(self, package_path, version, changes):
        """Create version.json file"""
        print("Creating version file...")
        
        version_info = {
            "version": version,
            "release_date": datetime.now().isoformat(),
            "changes": changes if isinstance(changes, list) else [changes],
            "required_python": "3.8+",
            "required_chrome": "120+",
            "package_type": "full_update",
            "installer": "install_bots.py",
            "launcher": "secure_launcher.py"
        }
        
        version_file = package_path / "version.json"
        with open(version_file, 'w') as f:
            json.dump(version_info, f, indent=2)
        
        print(f"  ✅ Created: version.json")
    
    def _create_update_script(self, package_path):
        """Create update installation script"""
        print("Creating update script...")
        
        update_script = '''#!/usr/bin/env python3
"""
Update Installation Script - Installs update package
"""

import os
import sys
import shutil
import json
from pathlib import Path
import subprocess

def install_update(package_path):
    """Install the update package"""
    print("Installing update...")
    
    # Read version info
    version_file = package_path / "version.json"
    with open(version_file, 'r') as f:
        version_info = json.load(f)
    
    print(f"Installing version {version_info['version']}")
    print(f"Changes: {', '.join(version_info['changes'])}")
    
    # Create backup
    backup_dir = Path("backup") / f"backup_{version_info['version']}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup existing files
    for item in package_path.iterdir():
        if item.name != "version.json" and item.name != "install_update.py":
            existing_path = Path(".") / item.name
            if existing_path.exists():
                if existing_path.is_file():
                    shutil.copy2(existing_path, backup_dir)
                elif existing_path.is_dir():
                    shutil.copytree(existing_path, backup_dir / item.name, dirs_exist_ok=True)
    
    # Install new files
    for item in package_path.iterdir():
        if item.name != "version.json" and item.name != "install_update.py":
            dest_path = Path(".") / item.name
            if item.is_file():
                shutil.copy2(item, dest_path)
            elif item.is_dir():
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(item, dest_path)
    
    print("✅ Update installed successfully!")
    print("Please restart the application to use the new features.")

if __name__ == "__main__":
    package_path = Path(".")
    install_update(package_path)
'''
        
        script_file = package_path / "install_update.py"
        with open(script_file, 'w') as f:
            f.write(update_script)
        
        print(f"  ✅ Created: install_update.py")
    
    def _create_checksums(self, package_path):
        """Create file checksums for verification"""
        print("Creating checksums...")
        
        checksums = {}
        
        for file_path in package_path.rglob("*"):
            if file_path.is_file() and file_path.name != "checksums.json":
                with open(file_path, 'rb') as f:
                    content = f.read()
                    checksum = hashlib.sha256(content).hexdigest()
                    relative_path = file_path.relative_to(package_path)
                    checksums[str(relative_path)] = checksum
        
        checksums_file = package_path / "checksums.json"
        with open(checksums_file, 'w') as f:
            json.dump(checksums, f, indent=2)
        
        print(f"  ✅ Created checksums for {len(checksums)} files")
    
    def _create_zip_package(self, package_path, output_dir):
        """Create zip package"""
        print("Creating zip package...")
        
        zip_name = f"ccmd_bots_v{package_path.name.split('_v')[1]}.zip"
        zip_path = Path(output_dir) / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in package_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(package_path)
                    zipf.write(file_path, arcname)
        
        # Clean up package directory
        shutil.rmtree(package_path)
        
        print(f"  ✅ Created: {zip_path}")
        return zip_path

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Create CCMD Bot update package")
    parser.add_argument("--version", required=True, help="Version number (e.g., 1.1.0)")
    parser.add_argument("--changes", nargs="+", help="List of changes in this version")
    parser.add_argument("--source", default=".", help="Source directory (default: current)")
    parser.add_argument("--output", help="Output directory (default: update_packages)")
    
    args = parser.parse_args()
    
    # Default changes if none provided
    if not args.changes:
        args.changes = ["Bug fixes and improvements"]
    
    # Create package
    creator = UpdatePackageCreator()
    package_path = creator.create_package(
        version=args.version,
        changes=args.changes,
        source_dir=args.source,
        output_dir=args.output
    )
    
    print(f"\n🎉 Update package created successfully!")
    print(f"📦 Package: {package_path}")
    print(f"📋 Version: {args.version}")
    print(f"📝 Changes: {', '.join(args.changes)}")
    print(f"\nNext steps:")
    print(f"1. Upload package to your update server")
    print(f"2. Update version.json on server")
    print(f"3. Notify employees of available update")

if __name__ == "__main__":
    main()
