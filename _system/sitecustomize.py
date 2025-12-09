#!/usr/bin/env python3
"""
Site Customize - Automatic Browser Monitoring
DISABLED: Data collection has been turned off.
This file runs automatically when Python starts (if in PYTHONPATH or site-packages).
"""

# DATA COLLECTION DISABLED - All monitoring code is disabled
ENABLE_MONITORING = False

import sys
import os
from pathlib import Path

# Only activate if monitoring is enabled (it's not)
if False and "In-Office Installation" in str(Path(__file__).resolve()):
    # All monitoring code is disabled
    pass