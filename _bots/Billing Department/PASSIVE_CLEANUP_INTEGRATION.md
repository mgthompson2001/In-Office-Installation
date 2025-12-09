# Passive Data Cleanup Integration Guide

## Overview

The passive data cleanup system automatically manages storage across **ALL bots** in your installation. It removes unnecessary data (old backups, test files, logs, database records) based on retention policies.

## Quick Integration (2 Lines of Code!)

Add these 2 lines to any bot's initialization:

```python
from init_passive_cleanup import init_passive_cleanup
init_passive_cleanup()
```

That's it! Cleanup runs automatically in the background when the bot starts.

## Integration Examples

### Example 1: Simple Bot (No Logger)

```python
#!/usr/bin/env python3
"""My Bot"""

# ... your imports ...

# Add passive cleanup (at top of file or in __init__)
from init_passive_cleanup import init_passive_cleanup

def main():
    # Initialize cleanup (runs in background, non-blocking)
    init_passive_cleanup()
    
    # ... rest of your bot code ...

if __name__ == "__main__":
    main()
```

### Example 2: Bot with Logger

```python
#!/usr/bin/env python3
"""My Bot"""

import logging
from init_passive_cleanup import init_passive_cleanup

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MyBot:
    def __init__(self):
        # Initialize cleanup with logger
        init_passive_cleanup(logger=logger)
        
        # ... rest of initialization ...

if __name__ == "__main__":
    bot = MyBot()
```

### Example 3: Bot with Custom Installation Directory

```python
from pathlib import Path
from init_passive_cleanup import init_passive_cleanup

# If your bot needs to specify installation directory
installation_dir = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")
init_passive_cleanup(installation_dir=installation_dir)
```

## Where to Add It

### Option 1: In `__init__` method (Recommended)
```python
class MyBot:
    def __init__(self):
        init_passive_cleanup()  # Add here
        # ... rest of initialization ...
```

### Option 2: In `main()` function
```python
def main():
    init_passive_cleanup()  # Add here
    # ... rest of main code ...
```

### Option 3: At module level (if bot doesn't use classes)
```python
# At top of file, after imports
from init_passive_cleanup import init_passive_cleanup
init_passive_cleanup()
```

## How It Works

1. **Non-blocking**: Runs in a background thread, doesn't slow down bot startup
2. **Automatic**: Cleans up across the entire installation directory
3. **Safe**: Only removes old files based on retention policies
4. **Silent**: Only logs when significant cleanup occurs (>0.1 MB freed)

## What Gets Cleaned

| Data Type | Retention | Location |
|-----------|-----------|----------|
| Browser Activity DB | 30 days | All `_secure_data/browser_activity.db` files |
| Backup Files | 7 days | All `*.backup-*.json`, `*.backup-*.db`, `*.backup-*.log` |
| Test Files | 1 day | All `test_*.py`, `temp_*.py`, `*_test.py` |
| Log Files | 14 days | All `*.log`, `*.log.*` files |

## Protected Directories

These directories are **never** cleaned:
- `quarantine/`
- `__pycache__/`
- `.git/`
- `Cursor versions/`
- `Past Logs/`
- `Example Log/`

## Customization

To adjust retention periods, edit `AI/monitoring/data_cleanup.py` (root AI folder):

```python
class DataCleanupManager:
    DATABASE_RETENTION_DAYS = 30  # Change as needed
    BACKUP_RETENTION_DAYS = 7     # Change as needed
    LOG_RETENTION_DAYS = 14       # Change as needed
    TEST_FILE_RETENTION_DAYS = 1  # Change as needed
```

## Troubleshooting

**Import Error?**
- Make sure `init_passive_cleanup.py` is in the `_bots` directory
- Check that your bot can access the `_bots` directory

**Cleanup not running?**
- Check bot logs for errors
- Verify the function is being called
- Check file permissions

**Too aggressive/not aggressive enough?**
- Adjust retention periods in `data_cleanup.py`
- Check what files are being deleted in logs

## Files

- `AI/monitoring/data_cleanup.py` - Main cleanup utility (root AI folder)
- `AI/monitoring/browser_activity_monitor.py` - Browser monitoring (root AI folder)
- `_bots/init_passive_cleanup.py` - Easy integration helper for all bots
- `_bots/PASSIVE_CLEANUP_INTEGRATION.md` - This file

## Status

✅ **Medisoft Billing Bot** - Already integrated
⏳ **Other bots** - Add the 2 lines of code shown above

