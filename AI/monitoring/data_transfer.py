#!/usr/bin/env python3
"""
Data Transfer Module - Transfers collected data from employee computers to central location.
"""

import json
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

_LOGGER = logging.getLogger("data_transfer")

class DataTransferManager:
    """Manages transfer of training data from employee computers to central location."""
    
    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.ai_dir = self.installation_dir / "AI"
        self.training_data_dir = self.ai_dir / "training_data"
        
    def transfer_data_to_central(self, central_path: Path, computer_id: str) -> Dict[str, Any]:
        """Transfer all training data to central location.
        
        Args:
            central_path: Path to central data folder
            computer_id: Unique identifier for this computer
            
        Returns:
            Dictionary with transfer statistics
        """
        stats = {
            "files_transferred": 0,
            "bytes_transferred": 0,
            "errors": 0,
            "transferred_files": []
        }
        
        if not self.training_data_dir.exists():
            _LOGGER.debug("No training data directory found")
            return stats
        
        # Create computer-specific folder in central location
        computer_folder = central_path / computer_id
        computer_folder.mkdir(parents=True, exist_ok=True)
        
        # Transfer all training data files (processed data)
        training_files = list(self.training_data_dir.glob("*.json"))
        training_files.extend(list(self.training_data_dir.glob("*.json.gz")))
        
        # Also transfer raw coordinate files (workflow trainer data)
        coord_files = list(self.installation_dir.rglob("*_coordinates.json"))
        coord_files.extend(list(self.installation_dir.rglob("*coordinates*.json")))
        # Filter out files in protected directories
        coord_files = [f for f in coord_files if not any(skip in str(f) for skip in ['__pycache__', '.git', 'Cursor versions', 'Past Logs'])]
        training_files.extend(coord_files)
        
        # Also transfer screenshot/image files (workflow trainer data)
        image_extensions = ['.png', '.jpg', '.jpeg']
        for ext in image_extensions:
            image_files = list(self.installation_dir.rglob(f"*{ext}"))
            # Filter out files in protected directories and only include training screenshots
            image_files = [f for f in image_files if not any(skip in str(f) for skip in ['__pycache__', '.git', 'Cursor versions', 'Past Logs', 'vendor', 'node_modules'])]
            # Only include images in bot directories (likely training screenshots)
            image_files = [f for f in image_files if '_bots' in str(f) or 'Billing' in str(f) or 'Medisoft' in str(f)]
            training_files.extend(image_files)
        
        for source_file in training_files:
            try:
                # Create destination path with timestamp to avoid conflicts
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest_file = computer_folder / f"{timestamp}_{source_file.name}"
                
                # Copy file
                shutil.copy2(source_file, dest_file)
                
                # Verify copy
                if dest_file.exists() and dest_file.stat().st_size == source_file.stat().st_size:
                    stats["files_transferred"] += 1
                    stats["bytes_transferred"] += source_file.stat().st_size
                    stats["transferred_files"].append(str(dest_file))
                    _LOGGER.debug(f"Transferred: {source_file.name} -> {dest_file}")
                else:
                    stats["errors"] += 1
                    _LOGGER.warning(f"Transfer verification failed: {source_file.name}")
                    
            except Exception as e:
                stats["errors"] += 1
                _LOGGER.warning(f"Error transferring {source_file.name}: {e}")
        
        # Also transfer browser activity databases if they exist
        browser_db_dir = self.ai_dir / "browser_activity"
        if browser_db_dir.exists():
            db_files = list(browser_db_dir.glob("*.db"))
            for db_file in db_files:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest_file = computer_folder / "browser_activity" / f"{timestamp}_{db_file.name}"
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.copy2(db_file, dest_file)
                    
                    if dest_file.exists() and dest_file.stat().st_size == db_file.stat().st_size:
                        stats["files_transferred"] += 1
                        stats["bytes_transferred"] += db_file.stat().st_size
                        stats["transferred_files"].append(str(dest_file))
                except Exception as e:
                    stats["errors"] += 1
                    _LOGGER.warning(f"Error transferring database {db_file.name}: {e}")
        
        # Create transfer manifest
        manifest = {
            "computer_id": computer_id,
            "transfer_timestamp": datetime.now().isoformat(),
            "files_transferred": stats["files_transferred"],
            "bytes_transferred": stats["bytes_transferred"],
            "transferred_files": stats["transferred_files"]
        }
        
        manifest_file = computer_folder / f"transfer_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            _LOGGER.warning(f"Error creating transfer manifest: {e}")
        
        return stats
    
    def should_transfer(self, last_transfer_file: Path, interval_hours: int) -> bool:
        """Check if it's time to transfer data based on interval."""
        if not last_transfer_file.exists():
            return True
        
        try:
            with open(last_transfer_file, 'r', encoding='utf-8') as f:
                last_transfer = json.load(f)
            
            last_time_str = last_transfer.get("last_transfer")
            if not last_time_str:
                return True
            
            last_time = datetime.fromisoformat(last_time_str)
            time_since = datetime.now() - last_time
            
            return time_since >= timedelta(hours=interval_hours)
        except Exception:
            return True
    
    def record_transfer(self, last_transfer_file: Path) -> None:
        """Record the last transfer time."""
        try:
            last_transfer_file.parent.mkdir(parents=True, exist_ok=True)
            with open(last_transfer_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "last_transfer": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            _LOGGER.warning(f"Error recording transfer time: {e}")

