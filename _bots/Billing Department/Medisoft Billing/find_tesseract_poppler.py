#!/usr/bin/env python3
"""Find Tesseract and Poppler installations"""

import os
import subprocess
from pathlib import Path

print("=" * 60)
print("Searching for Tesseract and Poppler")
print("=" * 60)

# Common installation locations
search_paths = [
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path(os.environ.get("LOCALAPPDATA", "")),
    Path(os.environ.get("PROGRAMDATA", "")),
    Path(os.environ.get("USERPROFILE", "")),
    Path("C:/"),
]

# Check PATH environment variable
print("\n1. Checking PATH environment variable...")
path_dirs = os.environ.get("PATH", "").split(os.pathsep)
for path_dir in path_dirs:
    if path_dir:
        tesseract_path = Path(path_dir) / "tesseract.exe"
        poppler_path = Path(path_dir) / "pdftoppm.exe"
        if tesseract_path.exists():
            print(f"   [OK] Found tesseract.exe in PATH: {tesseract_path}")
        if poppler_path.exists():
            print(f"   [OK] Found pdftoppm.exe in PATH: {poppler_path}")

# Search common locations
print("\n2. Searching common installation locations...")

def find_files(root_path, filename, max_depth=3):
    """Recursively search for a file"""
    found = []
    root = Path(root_path)
    if not root.exists():
        return found
    
    try:
        for depth in range(max_depth):
            for path in root.rglob(filename):
                found.append(path)
                if len(found) >= 5:  # Limit results
                    return found
    except (PermissionError, OSError):
        pass
    return found

# Search for Tesseract
print("\n   Searching for tesseract.exe...")
tesseract_files = []
for search_path in search_paths:
    if search_path.exists():
        found = find_files(search_path, "tesseract.exe", max_depth=3)
        tesseract_files.extend(found)
        if len(tesseract_files) >= 3:
            break

if tesseract_files:
    for tesseract in tesseract_files[:3]:
        print(f"   [OK] Found: {tesseract}")
        # Get parent bin directory
        tesseract_dir = tesseract.parent
        print(f"      Directory: {tesseract_dir}")
        # Test if it works
        try:
            result = subprocess.run([str(tesseract), "--version"], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.decode('utf-8', errors='ignore').split('\n')[0]
                print(f"      Version: {version}")
        except:
            pass
else:
    print("   [X] tesseract.exe not found")

# Search for Poppler
print("\n   Searching for pdftoppm.exe (Poppler)...")
poppler_files = []
for search_path in search_paths:
    if search_path.exists():
        found = find_files(search_path, "pdftoppm.exe", max_depth=3)
        poppler_files.extend(found)
        if len(poppler_files) >= 3:
            break

if poppler_files:
    for poppler in poppler_files[:3]:
        print(f"   [OK] Found: {poppler}")
        # Get parent bin directory
        poppler_dir = poppler.parent
        print(f"      Directory: {poppler_dir}")
else:
    print("   [X] pdftoppm.exe not found (Poppler)")

# Check if Tesseract is installed via conda/anaconda
print("\n3. Checking for conda/anaconda installations...")
conda_paths = [
    Path(os.environ.get("CONDA_PREFIX", "")),
    Path(os.environ.get("ANACONDA_HOME", "")),
]
for conda_path in conda_paths:
    if conda_path.exists():
        tesseract = conda_path / "Library" / "bin" / "tesseract.exe"
        if tesseract.exists():
            print(f"   [OK] Found Tesseract in conda: {tesseract}")
        poppler_bin = conda_path / "Library" / "bin"
        poppler_exe = poppler_bin / "pdftoppm.exe"
        if poppler_exe.exists():
            print(f"   [OK] Found Poppler in conda: {poppler_exe}")
            print(f"      Set POPPLER_PATH to: {poppler_bin}")

print("\n" + "=" * 60)
print("Recommendations:")
print("=" * 60)

if tesseract_files:
    tesseract_dir = tesseract_files[0].parent
    print(f"\nFor Tesseract, add this to your bot code:")
    print(f"   pytesseract.pytesseract.tesseract_cmd = r'{tesseract_files[0]}'")
else:
    print("\nTesseract not found. Please provide the installation path.")

if poppler_files:
    poppler_dir = poppler_files[0].parent
    print(f"\nFor Poppler, set environment variable or add to bot code:")
    print(f"   POPPLER_PATH = r'{poppler_dir}'")
    print(f"\nOr set it before running the bot:")
    print(f"   import os")
    print(f"   os.environ['POPPLER_PATH'] = r'{poppler_dir}'")
else:
    print("\nPoppler not found. Please provide the installation path.")

