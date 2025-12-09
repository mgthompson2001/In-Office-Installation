#!/usr/bin/env python3
"""
Check Python version compatibility
Returns 0 if compatible, 1 if not
"""

import sys
import subprocess

def check_python_compatible():
    """Check if current Python version is compatible (3.7 - 3.12)"""
    version = sys.version_info
    
    if version.major == 3 and 7 <= version.minor <= 12:
        print(f"Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return 0
    else:
        print(f"Python {version.major}.{version.minor}.{version.micro} - NOT Compatible")
        print("Required: Python 3.7 - 3.12")
        print("Recommended: Python 3.10 or 3.11")
        return 1

if __name__ == "__main__":
    sys.exit(check_python_compatible())

