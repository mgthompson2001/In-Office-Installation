#!/usr/bin/env python3
"""
Consolidate Test Files - Move all test files to a centralized testing folder
"""

import shutil
from pathlib import Path

# Installation directory
INSTALLATION_DIR = Path(__file__).parent

# Testing folder in AI directory
TESTING_FOLDER = INSTALLATION_DIR / "AI" / "testing"
TESTING_FOLDER.mkdir(exist_ok=True, parents=True)

# Subdirectories for different types of tests
TEST_SUBFOLDERS = {
    "system": TESTING_FOLDER / "system",
    "bots": TESTING_FOLDER / "bots",
    "integration": TESTING_FOLDER / "integration"
}

# Create subdirectories
for folder in TEST_SUBFOLDERS.values():
    folder.mkdir(exist_ok=True, parents=True)

# Test files to move from _system
SYSTEM_TEST_FILES = [
    "test_desktop_shortcut.py",
    "test_desktop_shortcut.bat",
    "test_user_registration.py",
    "test_user_registration.bat",
    "test_employee_installation.bat",
    "test_installer.py",
]

# Test files to move from _bots
BOTS_TEST_FILES = [
    "test_bot_monitoring.py",
]

def move_file(source: Path, dest: Path):
    """Move a file"""
    if not source.exists():
        return False
    
    try:
        if dest.exists():
            print(f"  Warning: {dest.name} already exists, skipping...")
            return False
        
        dest.parent.mkdir(exist_ok=True, parents=True)
        shutil.move(str(source), str(dest))
        print(f"  Moved: {source.name} -> {dest}")
        return True
    except Exception as e:
        print(f"  Error moving {source.name}: {e}")
        return False

def main():
    """Main consolidation function"""
    print("=" * 60)
    print("CONSOLIDATING TEST FILES")
    print("=" * 60)
    print()
    
    moved_count = 0
    
    # Move system test files
    print("Moving system test files...")
    system_dir = INSTALLATION_DIR / "_system"
    for file_name in SYSTEM_TEST_FILES:
        source = system_dir / file_name
        dest = TEST_SUBFOLDERS["system"] / file_name
        if move_file(source, dest):
            moved_count += 1
    print()
    
    # Move bot test files
    print("Moving bot test files...")
    bots_dir = INSTALLATION_DIR / "_bots"
    for file_name in BOTS_TEST_FILES:
        source = bots_dir / file_name
        dest = TEST_SUBFOLDERS["bots"] / file_name
        if move_file(source, dest):
            moved_count += 1
    print()
    
    print("=" * 60)
    print(f"CONSOLIDATION COMPLETE")
    print(f"Moved {moved_count} test files to AI/testing")
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()

