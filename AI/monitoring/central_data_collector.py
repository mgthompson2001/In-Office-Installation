#!/usr/bin/env python3
"""
Central Data Collector - Processes incoming data from employee computers.
"""

import json
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

_LOGGER = logging.getLogger("central_collector")

class CentralDataCollector:
    """Collects and processes data from employee computers."""
    
    def __init__(self, installation_dir: Path, central_data_path: Path):
        self.installation_dir = Path(installation_dir)
        self.central_data_path = Path(central_data_path)
        self.ai_dir = self.installation_dir / "AI"
        self.training_data_dir = self.ai_dir / "training_data"
        
    def collect_employee_data(self) -> Dict[str, Any]:
        """Collect all data from employee computer folders and move to central training data."""
        stats = {
            "computers_processed": 0,
            "files_collected": 0,
            "bytes_collected": 0,
            "errors": 0
        }
        
        if not self.central_data_path.exists():
            _LOGGER.warning(f"Central data path does not exist: {self.central_data_path}")
            return stats
        
        # Ensure training data directory exists
        self.training_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each computer folder
        for computer_folder in self.central_data_path.iterdir():
            if not computer_folder.is_dir():
                continue
            
            computer_id = computer_folder.name
            _LOGGER.info(f"Processing data from computer: {computer_id}")
            
            try:
                # Collect training data files
                for data_file in computer_folder.glob("*.json"):
                    if "transfer_manifest" in data_file.name:
                        continue  # Skip manifest files
                    
                    try:
                        # Move to central training data directory
                        dest_file = self.training_data_dir / f"{computer_id}_{data_file.name}"
                        shutil.move(str(data_file), str(dest_file))
                        
                        stats["files_collected"] += 1
                        stats["bytes_collected"] += dest_file.stat().st_size
                        _LOGGER.debug(f"Collected: {data_file.name}")
                    except Exception as e:
                        stats["errors"] += 1
                        _LOGGER.warning(f"Error collecting {data_file.name}: {e}")
                
                # Collect compressed files
                for data_file in computer_folder.glob("*.json.gz"):
                    try:
                        dest_file = self.training_data_dir / f"{computer_id}_{data_file.name}"
                        shutil.move(str(data_file), str(dest_file))
                        
                        stats["files_collected"] += 1
                        stats["bytes_collected"] += dest_file.stat().st_size
                    except Exception as e:
                        stats["errors"] += 1
                        _LOGGER.warning(f"Error collecting {data_file.name}: {e}")
                
                # Collect browser activity databases
                browser_activity_dir = computer_folder / "browser_activity"
                if browser_activity_dir.exists():
                    central_browser_dir = self.ai_dir / "browser_activity" / computer_id
                    central_browser_dir.mkdir(parents=True, exist_ok=True)
                    
                    for db_file in browser_activity_dir.glob("*.db"):
                        try:
                            dest_file = central_browser_dir / db_file.name
                            shutil.move(str(db_file), str(dest_file))
                            
                            stats["files_collected"] += 1
                            stats["bytes_collected"] += dest_file.stat().st_size
                        except Exception as e:
                            stats["errors"] += 1
                            _LOGGER.warning(f"Error collecting database {db_file.name}: {e}")
                
                # Clean up empty folders and manifest files
                try:
                    for manifest_file in computer_folder.glob("transfer_manifest_*.json"):
                        manifest_file.unlink()  # Delete manifest after processing
                    
                    # Remove empty computer folder
                    if not any(computer_folder.iterdir()):
                        computer_folder.rmdir()
                except Exception:
                    pass  # Ignore cleanup errors
                
                stats["computers_processed"] += 1
                
            except Exception as e:
                stats["errors"] += 1
                _LOGGER.warning(f"Error processing computer {computer_id}: {e}")
        
        _LOGGER.info(f"Collection complete: {stats['computers_processed']} computers, "
                    f"{stats['files_collected']} files, "
                    f"{stats['bytes_collected'] / (1024*1024):.2f} MB")
        
        return stats

