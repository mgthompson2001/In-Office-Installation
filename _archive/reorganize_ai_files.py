#!/usr/bin/env python3
"""
Reorganize AI Files - Consolidate and organize AI-related files
Moves all AI-related materials into a centralized AI folder
"""

import shutil
from pathlib import Path
import sys

# Installation directory
INSTALLATION_DIR = Path(__file__).parent

# New AI folder
AI_FOLDER = INSTALLATION_DIR / "AI"
AI_FOLDER.mkdir(exist_ok=True)

# Subdirectories in AI folder
AI_SUBFOLDERS = {
    "monitoring": AI_FOLDER / "monitoring",
    "training": AI_FOLDER / "training",
    "intelligence": AI_FOLDER / "intelligence",
    "models": AI_FOLDER / "models",
    "data": AI_FOLDER / "data",
    "testing": AI_FOLDER / "testing",
    "scripts": AI_FOLDER / "scripts"
}

# Create subdirectories
for folder in AI_SUBFOLDERS.values():
    folder.mkdir(exist_ok=True, parents=True)

# Files to move from root
ROOT_AI_FILES = [
    "MASTER_AI_DASHBOARD.py",
    "LAUNCH_MASTER_AI_DASHBOARD.bat"
]

# Directories to move
DIRECTORIES_TO_MOVE = {
    "_ai_intelligence": AI_SUBFOLDERS["intelligence"],
    "_ai_models": AI_SUBFOLDERS["models"],
}

# Files from _system to move
SYSTEM_AI_FILES = {
    # Monitoring
    "full_system_monitor.py": AI_SUBFOLDERS["monitoring"],
    "full_monitoring_gui.py": AI_SUBFOLDERS["monitoring"],
    "launch_full_monitoring.bat": AI_SUBFOLDERS["monitoring"],
    "install_full_monitoring.bat": AI_SUBFOLDERS["monitoring"],
    "verify_full_monitoring_dependencies.py": AI_SUBFOLDERS["monitoring"],
    "FULL_SYSTEM_MONITORING.md": AI_SUBFOLDERS["monitoring"],
    "browser_activity_monitor.py": AI_SUBFOLDERS["monitoring"],
    "auto_webdriver_wrapper.py": AI_SUBFOLDERS["monitoring"],
    "selenium_auto_wrapper.py": AI_SUBFOLDERS["monitoring"],
    "auto_diagnostic_monitor.py": AI_SUBFOLDERS["monitoring"],
    "diagnose_browser_monitoring.py": AI_SUBFOLDERS["monitoring"],
    "diagnose_browser_monitoring.bat": AI_SUBFOLDERS["monitoring"],
    "test_browser_monitoring.py": AI_SUBFOLDERS["testing"],
    "test_browser_monitoring.bat": AI_SUBFOLDERS["testing"],
    "test_browser_recording_live.py": AI_SUBFOLDERS["testing"],
    "test_monitoring_with_launch.py": AI_SUBFOLDERS["testing"],
    "verify_browser_activity.py": AI_SUBFOLDERS["monitoring"],
    "verify_browser_activity.bat": AI_SUBFOLDERS["monitoring"],
    "check_browser_data.py": AI_SUBFOLDERS["monitoring"],
    "analyze_browser_data.py": AI_SUBFOLDERS["monitoring"],
    "analyze_browser_data.bat": AI_SUBFOLDERS["monitoring"],
    "BROWSER_ACTIVITY_MONITORING.md": AI_SUBFOLDERS["monitoring"],
    "BROWSER_RECORDING_FIXED.md": AI_SUBFOLDERS["monitoring"],
    
    # Training
    "ai_training_integration.py": AI_SUBFOLDERS["training"],
    "local_ai_trainer.py": AI_SUBFOLDERS["training"],
    "ai_activity_analyzer.py": AI_SUBFOLDERS["training"],
    "pattern_extraction_engine.py": AI_SUBFOLDERS["training"],
    "intelligent_learning.py": AI_SUBFOLDERS["training"],
    
    # Intelligence
    "ai_intelligence_gui.py": AI_SUBFOLDERS["intelligence"],
    "verify_ai_intelligence.py": AI_SUBFOLDERS["intelligence"],
    "view_ai_intelligence.bat": AI_SUBFOLDERS["intelligence"],
    "launch_ai_intelligence.bat": AI_SUBFOLDERS["intelligence"],
    "ai_task_assistant.py": AI_SUBFOLDERS["intelligence"],
    "ai_task_assistant_gui.py": AI_SUBFOLDERS["intelligence"],
    "ai_agent.py": AI_SUBFOLDERS["intelligence"],
    "ai_optimization_analyzer.py": AI_SUBFOLDERS["intelligence"],
    "autonomous_ai_engine.py": AI_SUBFOLDERS["intelligence"],
    "csuite_ai_modules.py": AI_SUBFOLDERS["intelligence"],
    "verify_ai_installation.py": AI_SUBFOLDERS["testing"],
    "setup_ai_api_keys.py": AI_SUBFOLDERS["scripts"],
    "setup_ai_api_keys.bat": AI_SUBFOLDERS["scripts"],
    "AI_TASK_ASSISTANT_README.md": AI_SUBFOLDERS["intelligence"],
    "AI_TECH_STACK_OVERVIEW.md": AI_SUBFOLDERS["intelligence"],
    "AUTONOMOUS_AI_ARCHITECTURE.md": AI_SUBFOLDERS["intelligence"],
    "AUTONOMOUS_LEARNING_EXPLAINED.md": AI_SUBFOLDERS["intelligence"],
    "ENTERPRISE_AI_FEATURES.md": AI_SUBFOLDERS["intelligence"],
    
    # Testing
    "test_bot_recording.py": AI_SUBFOLDERS["testing"],
    "test_bot_recording.bat": AI_SUBFOLDERS["testing"],
    "test_browser_integration.py": AI_SUBFOLDERS["testing"],
    "test_direct_launch.py": AI_SUBFOLDERS["testing"],
    "test_universal_bridge.py": AI_SUBFOLDERS["testing"],
    "verify_data_collection.py": AI_SUBFOLDERS["testing"],
}

# Data directories to move
DATA_DIRECTORIES = {
    "_secure_data/full_monitoring": AI_SUBFOLDERS["data"] / "full_monitoring",
    "_secure_data/browser_activity.db": AI_SUBFOLDERS["data"] / "browser_activity.db",
    "_secure_data/browser_activity.log": AI_SUBFOLDERS["data"] / "browser_activity.log",
    "_secure_data/diagnostic_monitor.log": AI_SUBFOLDERS["data"] / "diagnostic_monitor.log",
}

def move_file(source: Path, dest: Path, create_dest_dir: bool = True):
    """Move a file, creating destination directory if needed"""
    if not source.exists():
        return False
    
    if create_dest_dir:
        dest.parent.mkdir(exist_ok=True, parents=True)
    
    try:
        if dest.exists():
            print(f"  Warning: {dest.name} already exists, skipping...")
            return False
        
        shutil.move(str(source), str(dest))
        print(f"  Moved: {source.name} -> {dest}")
        return True
    except Exception as e:
        print(f"  Error moving {source.name}: {e}")
        return False

def move_directory(source: Path, dest: Path):
    """Move a directory"""
    if not source.exists():
        return False
    
    try:
        if dest.exists():
            print(f"  Warning: {dest.name} already exists, merging...")
            # Merge contents
            for item in source.iterdir():
                dest_item = dest / item.name
                if item.is_dir():
                    if dest_item.exists():
                        move_directory(item, dest_item)
                    else:
                        shutil.move(str(item), str(dest_item))
                else:
                    if not dest_item.exists():
                        shutil.move(str(item), str(dest_item))
            # Remove source if empty
            try:
                source.rmdir()
            except:
                pass
        else:
            shutil.move(str(source), str(dest))
        print(f"  Moved directory: {source.name} -> {dest}")
        return True
    except Exception as e:
        print(f"  Error moving directory {source.name}: {e}")
        return False

def main():
    """Main reorganization function"""
    print("=" * 60)
    print("REORGANIZING AI FILES")
    print("=" * 60)
    print()
    
    moved_count = 0
    
    # Move root AI files
    print("Moving root AI files...")
    for file_name in ROOT_AI_FILES:
        source = INSTALLATION_DIR / file_name
        dest = AI_FOLDER / file_name
        if move_file(source, dest):
            moved_count += 1
    print()
    
    # Move directories
    print("Moving AI directories...")
    for source_dir, dest_dir in DIRECTORIES_TO_MOVE.items():
        source = INSTALLATION_DIR / source_dir
        if move_directory(source, dest_dir):
            moved_count += 1
    print()
    
    # Move files from _system
    print("Moving AI files from _system...")
    system_dir = INSTALLATION_DIR / "_system"
    for file_name, dest_dir in SYSTEM_AI_FILES.items():
        source = system_dir / file_name
        dest = dest_dir / file_name
        if move_file(source, dest):
            moved_count += 1
    print()
    
    # Move data directories
    print("Moving AI data directories...")
    for source_path, dest_path in DATA_DIRECTORIES.items():
        source = INSTALLATION_DIR / source_path
        if source.is_file():
            if move_file(source, dest_path):
                moved_count += 1
        elif source.is_dir():
            if move_directory(source, dest_path):
                moved_count += 1
    print()
    
    # Create README in AI folder
    readme_content = """# AI Folder - Centralized AI Development & Monitoring

This folder contains all AI-related materials for the In-Office Installation system.

## Structure

- **monitoring/**: Full system monitoring and browser activity monitoring
- **training/**: AI training integration and activity analysis
- **intelligence/**: AI intelligence dashboard and task assistant
- **models/**: Trained AI models
- **data/**: Collected monitoring data
- **testing/**: Test scripts and verification tools
- **scripts/**: Setup and configuration scripts

## Main Entry Points

- **MASTER_AI_DASHBOARD.py**: Master AI Dashboard (main interface)
- **LAUNCH_MASTER_AI_DASHBOARD.bat**: Launch script for Master Dashboard

## Usage

1. Launch Master AI Dashboard: Double-click `LAUNCH_MASTER_AI_DASHBOARD.bat`
2. Launch Full System Monitoring: Use the button in Master Dashboard
3. View AI Intelligence: Use the tabs in Master Dashboard

All AI development and monitoring is now centralized in this folder.
"""
    
    readme_file = AI_FOLDER / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"Created README.md in AI folder")
    print()
    
    print("=" * 60)
    print(f"REORGANIZATION COMPLETE")
    print(f"Moved {moved_count} items to AI folder")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Update any scripts that reference moved files")
    print("2. Test the Master AI Dashboard")
    print("3. Verify all AI functionality still works")
    print()

if __name__ == "__main__":
    main()

