#!/usr/bin/env python3
"""
Create .bat wrapper files for all Python bots
This allows bots to be double-clicked and run with the correct Python interpreter
"""

import os
import sys
from pathlib import Path
import subprocess

def create_bat_wrapper(python_file_path, bat_file_path, description=""):
    """Create a .bat wrapper for a Python file"""
    
    python_file = Path(python_file_path)
    bat_file = Path(bat_file_path)
    
    # Calculate how many directories up to get to _bots from this bot file
    # We need to find _bots folder, then go to installation root
    path_parts = list(python_file.parent.parts)
    
    # Find where _bots is in the path
    try:
        bots_index = path_parts.index('_bots')
        # Everything after _bots is the relative path within _bots
        relative_within_bots = Path(*path_parts[bots_index+1:]) / python_file.name
    except ValueError:
        # If no _bots in path, just use the full path
        relative_within_bots = python_file
    
    # Create batch file content
    # Uses ~dp0 to get .bat file location, then navigates relative to it
    bat_content = f'''@echo off
REM {description}
REM Auto-generated batch wrapper for: {python_file.name}

echo Starting {python_file.name}...
echo.

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory (where the bot is located)
cd /d "%SCRIPT_DIR%"

REM Run the Python script (will use python from PATH)
python "{python_file.name}"

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred! Press any key to close...
    pause > nul
)
'''
    
    # Write the batch file
    with open(bat_file, 'w') as f:
        f.write(bat_content)
    
    print(f"[OK] Created: {bat_file.name}")

def get_python_files(root_dir):
    """Find all Python files in the _bots directory"""
    python_files = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip cache and other system folders only
        if any(x in root for x in ['__pycache__', '.git']):
            continue
            
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                full_path = Path(root) / file
                python_files.append(full_path)
    
    return python_files

def main():
    """Main function to create batch wrappers"""
    print("=" * 60)
    print("Creating .bat Wrappers for All Bots")
    print("=" * 60)
    print()
    
    # Get installation directory
    install_dir = Path(__file__).parent.parent
    
    # Get _bots directory
    bots_dir = install_dir / "_bots"
    
    if not bots_dir.exists():
        print(f"[ERROR] _bots directory not found: {bots_dir}")
        return False
    
    # Find all Python files
    python_files = get_python_files(bots_dir)
    
    if not python_files:
        print("[WARN] No Python files found in _bots directory")
        return False
    
    print(f"Found {len(python_files)} Python files to wrap")
    print()
    
    created_count = 0
    skipped_count = 0
    
    for python_file in python_files:
        # Create bat file path (same location, different extension)
        bat_file = python_file.with_suffix('.bat')
        
        # Skip if already exists
        if bat_file.exists():
            skipped_count += 1
            continue
        
        # Create wrapper
        create_bat_wrapper(python_file, bat_file, f"Wrapper for {python_file.name}")
        created_count += 1
    
    print()
    print("=" * 60)
    print(f"[OK] Created {created_count} batch files")
    print(f"[SKIP] Skipped {skipped_count} existing batch files")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            input("Press ENTER to exit...")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        input("Press ENTER to exit...")
