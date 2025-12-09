"""
Auto-Update Manager for Bots
Handles checking for updates, downloading, and installing them automatically.
Preserves user data (credentials, settings, saved selectors).
"""

import json
import os
import shutil
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, Dict, List
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

class UpdateManager:
    """Manages automatic updates for bots."""
    
    def __init__(self, bot_name: str, current_version: str, update_source: str, 
                 bot_directory: Path, user_data_files: List[str] = None):
        """
        Initialize the update manager.
        
        Args:
            bot_name: Name of the bot (e.g., "Medisoft Billing Bot")
            current_version: Current version string (e.g., "1.0.0")
            update_source: Path to update source (G-Drive path, OneDrive path, URL, or network path)
            bot_directory: Directory where bot is installed
            user_data_files: List of files to preserve during updates (e.g., ["medisoft_users.json"])
        """
        self.bot_name = bot_name
        self.current_version = current_version
        self.update_source = update_source
        self.bot_directory = Path(bot_directory)
        self.user_data_files = user_data_files or []
        
        # Create update directory
        self.update_dir = self.bot_directory / "_updates"
        self.update_dir.mkdir(exist_ok=True)
        
        # Version file location
        self.version_file = self.bot_directory / "version.json"
        self.manifest_file = self.update_dir / "update_manifest.json"
        
    def get_current_version(self) -> str:
        """Get the current installed version."""
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r') as f:
                    data = json.load(f)
                    return data.get('version', self.current_version)
            except:
                pass
        return self.current_version
    
    def save_version(self, version: str):
        """Save the current version to file."""
        version_data = {
            'version': version,
            'updated': datetime.now().isoformat(),
            'bot_name': self.bot_name
        }
        with open(self.version_file, 'w') as f:
            json.dump(version_data, f, indent=2)
    
    def check_for_updates(self) -> Optional[Dict]:
        """
        Check if updates are available.
        
        Returns:
            Update info dict if update available, None otherwise
        """
        try:
            # Try to read version info from update source
            version_info_path = Path(self.update_source) / "version.json"
            
            if not version_info_path.exists():
                logger.warning(f"Version file not found at {version_info_path}")
                return None
            
            with open(version_info_path, 'r') as f:
                remote_version_info = json.load(f)
            
            remote_version = remote_version_info.get('version', '0.0.0')
            current_version = self.get_current_version()
            
            if self._compare_versions(remote_version, current_version) > 0:
                return {
                    'available': True,
                    'current_version': current_version,
                    'new_version': remote_version,
                    'release_notes': remote_version_info.get('release_notes', ''),
                    'update_url': str(version_info_path.parent),
                    'manifest_file': str(Path(self.update_source) / "update_manifest.json")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return None
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.
        
        Returns:
            1 if v1 > v2, -1 if v1 < v2, 0 if equal
        """
        def version_tuple(v):
            return tuple(map(int, (v.split("."))))
        
        try:
            v1_tuple = version_tuple(v1)
            v2_tuple = version_tuple(v2)
            
            if v1_tuple > v2_tuple:
                return 1
            elif v1_tuple < v2_tuple:
                return -1
            else:
                return 0
        except:
            # If version format is unexpected, compare as strings
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
            else:
                return 0
    
    def backup_user_data(self) -> Path:
        """Backup user data files before update."""
        backup_dir = self.update_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(exist_ok=True)
        
        backed_up = []
        for data_file in self.user_data_files:
            source = self.bot_directory / data_file
            if source.exists():
                dest = backup_dir / data_file
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
                backed_up.append(data_file)
                logger.info(f"Backed up: {data_file}")
        
        # Save backup manifest
        backup_manifest = {
            'timestamp': datetime.now().isoformat(),
            'files': backed_up
        }
        with open(backup_dir / "backup_manifest.json", 'w') as f:
            json.dump(backup_manifest, f, indent=2)
        
        return backup_dir
    
    def restore_user_data(self, backup_dir: Path):
        """Restore user data files after update."""
        backup_manifest_file = backup_dir / "backup_manifest.json"
        if not backup_manifest_file.exists():
            logger.warning("Backup manifest not found, attempting to restore all files")
            # Try to restore all files in backup directory
            for file_path in backup_dir.rglob("*"):
                if file_path.is_file() and file_path.name != "backup_manifest.json":
                    relative_path = file_path.relative_to(backup_dir)
                    dest = self.bot_directory / relative_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest)
                    logger.info(f"Restored: {relative_path}")
        else:
            with open(backup_manifest_file, 'r') as f:
                backup_manifest = json.load(f)
            
            for data_file in backup_manifest.get('files', []):
                source = backup_dir / data_file
                if source.exists():
                    dest = self.bot_directory / data_file
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    logger.info(f"Restored: {data_file}")
    
    def download_update(self, update_info: Dict) -> bool:
        """
        Download update files.
        
        Args:
            update_info: Update info from check_for_updates()
        
        Returns:
            True if download successful, False otherwise
        """
        try:
            update_source_path = Path(update_info['update_url'])
            manifest_path = Path(update_info['manifest_file'])
            
            if not manifest_path.exists():
                logger.error(f"Update manifest not found: {manifest_path}")
                return False
            
            # Read manifest
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            files_to_update = manifest.get('files', [])
            
            # Download/copy each file
            for file_info in files_to_update:
                file_path = file_info.get('path', '')
                source_file = update_source_path / file_path
                dest_file = self.update_dir / file_path
                
                if not source_file.exists():
                    logger.warning(f"Source file not found: {source_file}")
                    continue
                
                # Create destination directory
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(source_file, dest_file)
                logger.info(f"Downloaded: {file_path}")
            
            # Save manifest to update directory
            shutil.copy2(manifest_path, self.manifest_file)
            
            return True
            
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            return False
    
    def install_update(self, update_info: Dict, ask_permission: bool = True) -> bool:
        """
        Install the downloaded update.
        
        Args:
            update_info: Update info from check_for_updates()
            ask_permission: Whether to ask user before installing
        
        Returns:
            True if installation successful, False otherwise
        """
        try:
            # Backup user data
            backup_dir = self.backup_user_data()
            logger.info(f"User data backed up to: {backup_dir}")
            
            # Read manifest
            if not self.manifest_file.exists():
                logger.error("Update manifest not found in update directory")
                return False
            
            with open(self.manifest_file, 'r') as f:
                manifest = json.load(f)
            
            files_to_update = manifest.get('files', [])
            
            # Install each file
            for file_info in files_to_update:
                file_path = file_info.get('path', '')
                source_file = self.update_dir / file_path
                dest_file = self.bot_directory / file_path
                
                if not source_file.exists():
                    logger.warning(f"Update file not found: {source_file}")
                    continue
                
                # Skip user data files (they'll be restored)
                if file_path in self.user_data_files:
                    logger.info(f"Skipping user data file: {file_path}")
                    continue
                
                # Create destination directory
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Backup existing file if it exists
                if dest_file.exists():
                    backup_file = backup_dir / file_path
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest_file, backup_file)
                
                # Copy new file
                shutil.copy2(source_file, dest_file)
                logger.info(f"Installed: {file_path}")
            
            # Restore user data
            self.restore_user_data(backup_dir)
            
            # Update version
            self.save_version(update_info['new_version'])
            
            logger.info(f"Update installed successfully: {update_info['new_version']}")
            return True
            
        except Exception as e:
            logger.error(f"Error installing update: {e}")
            # Try to restore from backup
            try:
                backup_dirs = sorted(self.update_dir.glob("backup_*"), reverse=True)
                if backup_dirs:
                    self.restore_user_data(backup_dirs[0])
                    logger.info("Restored from backup after failed update")
            except:
                pass
            return False
    
    def update(self, ask_permission: bool = True, auto_install: bool = False) -> Dict:
        """
        Check for and install updates.
        
        Args:
            ask_permission: Whether to ask user before installing
            auto_install: If True, install automatically without asking
        
        Returns:
            Dict with update status and information
        """
        result = {
            'update_available': False,
            'updated': False,
            'current_version': self.get_current_version(),
            'new_version': None,
            'error': None
        }
        
        # Check for updates
        update_info = self.check_for_updates()
        
        if not update_info:
            return result
        
        result['update_available'] = True
        result['new_version'] = update_info['new_version']
        
        if not auto_install and ask_permission:
            # In GUI applications, you would show a dialog here
            # For now, we'll return the update info
            return result
        
        # Download update
        if not self.download_update(update_info):
            result['error'] = "Failed to download update"
            return result
        
        # Install update
        if self.install_update(update_info, ask_permission=False):
            result['updated'] = True
        else:
            result['error'] = "Failed to install update"
        
        return result


def create_version_file(bot_directory: Path, version: str, bot_name: str, 
                       release_notes: str = ""):
    """
    Create a version.json file for the update system.
    
    Call this function when you want to release a new version.
    """
    version_data = {
        'version': version,
        'bot_name': bot_name,
        'release_date': datetime.now().isoformat(),
        'release_notes': release_notes
    }
    
    version_file = Path(bot_directory) / "version.json"
    with open(version_file, 'w') as f:
        json.dump(version_data, f, indent=2)
    
    print(f"Created version file: {version_file}")
    print(f"Version: {version}")


def create_update_manifest(bot_directory: Path, files_to_include: List[str] = None,
                          exclude_patterns: List[str] = None):
    """
    Create an update_manifest.json file listing all files to include in updates.
    
    Args:
        bot_directory: Root directory of the bot
        files_to_include: Specific files to include (if None, includes common bot files)
        exclude_patterns: Patterns to exclude (e.g., ["*.log", "__pycache__"])
    """
    bot_path = Path(bot_directory)
    
    if files_to_include is None:
        # Default: include common bot files
        files_to_include = [
            "*.py",
            "*.bat",
            "*.txt",
            "*.md",
            "requirements.txt",
            "Installer/**/*",
        ]
    
    if exclude_patterns is None:
        exclude_patterns = [
            "*.log",
            "*.json",  # User data files - will be handled separately
            "__pycache__",
            "*.pyc",
            ".git",
            "_updates",
            "vendor",
            "*.png",  # Saved selector images - preserve these
        ]
    
    files_list = []
    
    # Find all files
    for file_path in bot_path.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(bot_path)
            relative_str = str(relative_path).replace("\\", "/")
            
            # Check if excluded
            excluded = False
            for pattern in exclude_patterns:
                if pattern in relative_str or file_path.match(pattern):
                    excluded = True
                    break
            
            if not excluded:
                files_list.append({
                    'path': relative_str,
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
    
    manifest = {
        'created': datetime.now().isoformat(),
        'files': files_list,
        'total_files': len(files_list)
    }
    
    manifest_file = bot_path / "update_manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Created update manifest: {manifest_file}")
    print(f"Total files: {len(files_list)}")
    
    return manifest_file


if __name__ == "__main__":
    # Example usage
    print("Update Manager - Example Usage")
    print("=" * 50)
    
    # Example: Create version file for a release
    # create_version_file(
    #     bot_directory=Path(__file__).parent,
    #     version="1.0.1",
    #     bot_name="Medisoft Billing Bot",
    #     release_notes="Fixed bug in login process"
    # )
    
    # Example: Create update manifest
    # create_update_manifest(
    #     bot_directory=Path(__file__).parent,
    #     exclude_patterns=["*.log", "*.json", "__pycache__", "_updates"]
    # )
    
    print("\nTo use the update manager in your bot:")
    print("1. Import: from update_manager import UpdateManager")
    print("2. Initialize: manager = UpdateManager(...)")
    print("3. Check updates: update_info = manager.check_for_updates()")
    print("4. Install: manager.update()")

