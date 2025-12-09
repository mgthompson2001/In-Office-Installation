# Fix Wrong Central Data Path

## Problem

If an employee entered the wrong path during installation (like `G:\Company\Software\Misc\failed test log 11.24.25` instead of `G:\Company\Software\Training Data`), you need to fix it.

## Solution

On the employee computer, run this command:

```batch
python _tools\config\CONFIGURE_EMPLOYEE_MODE.py
```

Then:
1. Choose option 1 (Employee Computer)
2. Enter the **correct** path: `G:\Company\Software\Training Data`
3. Press Enter to accept default transfer interval (24 hours)

## Verify It's Fixed

Run this to check:
```batch
python _tools\config\CHECK_CONFIG_STATUS.py
```

You should see:
```
Central Data Path: G:\Company\Software\Training Data
✅ Central data folder exists and is accessible
```

## Quick Fix Command

You can also directly edit the config file:
1. Open: `AI\monitoring\system_config.json`
2. Change `central_data_path` to: `"G:\\Company\\Software\\Training Data"`
3. Save the file

Then verify with:
```batch
python _tools\config\CHECK_CONFIG_STATUS.py
```

