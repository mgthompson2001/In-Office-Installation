#!/usr/bin/env python3
"""
System Configuration - Determines if this is an employee computer or central training hub.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

_CONFIG_FILE = "system_config.json"
_CONFIG_KEYS = {
    "MODE": "mode",  # "employee" or "central"
    "CENTRAL_DATA_PATH": "central_data_path",  # Path to central data folder
    "TRANSFER_INTERVAL_HOURS": "transfer_interval_hours",  # How often to transfer data
    "COMPUTER_ID": "computer_id",  # Unique identifier for this computer
}

def get_config_path(installation_dir: Path) -> Path:
    """Get path to configuration file."""
    return installation_dir / "AI" / "monitoring" / _CONFIG_FILE

def load_config(installation_dir: Path) -> Dict[str, Any]:
    """Load system configuration."""
    config_path = get_config_path(installation_dir)
    
    if not config_path.exists():
        # Default: central mode (for existing installations)
        return {
            "mode": "central",
            "central_data_path": None,
            "transfer_interval_hours": 24,
            "computer_id": None,
        }
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception:
        # Return defaults on error
        return {
            "mode": "central",
            "central_data_path": None,
            "transfer_interval_hours": 24,
            "computer_id": None,
        }

def save_config(installation_dir: Path, config: Dict[str, Any]) -> bool:
    """Save system configuration."""
    try:
        config_path = get_config_path(installation_dir)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False

def is_employee_computer(installation_dir: Path) -> bool:
    """Check if this is an employee computer (data collection only)."""
    config = load_config(installation_dir)
    return config.get("mode", "central") == "employee"

def is_central_computer(installation_dir: Path) -> bool:
    """Check if this is the central training computer."""
    config = load_config(installation_dir)
    return config.get("mode", "central") == "central"

def get_central_data_path(installation_dir: Path) -> Optional[Path]:
    """Get the central data folder path (for employee computers)."""
    config = load_config(installation_dir)
    path_str = config.get("central_data_path")
    if not path_str:
        return None
    return Path(path_str)

def get_computer_id(installation_dir: Path) -> str:
    """Get or generate a unique computer ID."""
    config = load_config(installation_dir)
    computer_id = config.get("computer_id")
    
    if not computer_id:
        # Generate a unique ID based on computer name and user
        import socket
        import getpass
        computer_id = f"{socket.gethostname()}_{getpass.getuser()}"
        config["computer_id"] = computer_id
        save_config(installation_dir, config)
    
    return computer_id

def configure_employee_mode(
    installation_dir: Path,
    central_data_path: str,
    transfer_interval_hours: int = 24
) -> bool:
    """Configure this computer as an employee computer (data collection only)."""
    # Normalize the path - don't resolve network paths that may not exist yet
    try:
        # Try to resolve if it's a local path
        if not central_data_path.startswith('\\\\') and not central_data_path.startswith('G:'):
            central_path_str = str(Path(central_data_path).resolve())
        else:
            # For network paths, use as-is (they may not exist yet)
            central_path_str = str(Path(central_data_path))
    except:
        # If resolution fails, use as-is
        central_path_str = str(Path(central_data_path))
    
    config = {
        "mode": "employee",
        "central_data_path": central_path_str,
        "transfer_interval_hours": transfer_interval_hours,
        "computer_id": get_computer_id(installation_dir),  # Preserve existing ID
    }
    return save_config(installation_dir, config)

def configure_central_mode(installation_dir: Path) -> bool:
    """Configure this computer as the central training hub."""
    config = {
        "mode": "central",
        "central_data_path": None,
        "transfer_interval_hours": 24,
        "computer_id": get_computer_id(installation_dir),  # Preserve existing ID
    }
    return save_config(installation_dir, config)

