# Employee Installation Verification Guide

## When to Run Verification

**IMPORTANT: Run verification AFTER installation, not before!**

1. **First**: Employee runs `INSTALL_BOTS.bat` (this installs and configures everything)
2. **Then**: Employee runs verification to confirm it worked

## Quick Verification

After an employee runs `INSTALL_BOTS.bat`, verify the installation is working:

```batch
python _tools\config\VERIFY_EMPLOYEE_INSTALLATION.py
```

This script checks:
1. ✅ System configuration (employee mode)
2. ✅ Data collection setup
3. ✅ Training data directory
4. ✅ Transfer status
5. ✅ Bot integration
6. ✅ Network/path accessibility

## What to Look For

### ✅ Good Signs (Everything Working)

```
Mode: employee
Computer ID: COMPUTERNAME_USERNAME
Central Data Path: G:\Company\Software\Training Data
Transfer Interval: 24 hours

✅ Employee mode is configured
✅ Central data folder exists
✅ Passive cleanup system is installed
✅ Data collection setup is correct
✅ Bot integration is configured
✅ Can write to central data folder
```

### ⚠️ Warning Signs (Needs Attention)

- **Mode: NOT SET** → Run `python _tools\config\CONFIGURE_EMPLOYEE_MODE.py`
- **Central Data Path: NOT SET** → Employee mode not fully configured
- **Cannot write to central data folder** → Check network/permissions
- **Bot integration not configured** → Re-run installation

## Manual Verification Steps

### 1. Check Configuration File

Location: `AI\monitoring\system_config.json`

Should contain:
```json
{
  "mode": "employee",
  "central_data_path": "G:\\Company\\Software\\Training Data",
  "transfer_interval_hours": 24,
  "computer_id": "COMPUTERNAME_USERNAME"
}
```

### 2. Test Data Collection

1. Run any bot (e.g., Medisoft Billing Bot)
2. Wait 2-3 minutes
3. Check if data is being collected:
   ```batch
   dir AI\training_data
   ```
4. Should see JSON files appearing

### 3. Test Data Transfer

1. Wait for transfer interval (default: 24 hours)
2. Or manually trigger transfer by running a bot
3. Check central data folder:
   ```
   G:\Company\Software\Training Data\{computer_id}\
   ```
4. Should see transferred files

## Troubleshooting

### Issue: "Mode: NOT SET"

**Solution:**
```batch
python _tools\config\CONFIGURE_EMPLOYEE_MODE.py
```

### Issue: "Cannot write to central data folder"

**Solutions:**
1. Check network connectivity
2. Verify folder permissions
3. Test manually: Try creating a file in the central folder
4. Check if path is correct (network share vs local path)

### Issue: "No training data files"

**This is normal for new installations!**
- Data is collected when bots run
- Files appear in `AI\training_data\` after bot usage
- Wait for employees to use bots, then check again

### Issue: "Bot integration not configured"

**Solution:**
1. Check `_bots\__init__.py` exists
2. Re-run `INSTALL_BOTS.bat`
3. Contact IT support if issue persists

## For IT/Admin: Central Computer Verification

On the central computer, verify data is being received:

1. Check central data folder:
   ```
   G:\Company\Software\Training Data\
   ```
2. Should see folders for each employee computer:
   ```
   COMPUTER1_USERNAME\
   COMPUTER2_USERNAME\
   ...
   ```
3. Each folder should contain:
   - Training data files (`.json`)
   - Transfer manifests
   - Browser activity databases

## Expected Behavior

### When Employee Runs Bot:
1. Bot starts normally
2. Background thread starts data collection
3. Data is saved to `AI\training_data\`
4. No visible impact on bot performance

### Every 24 Hours (or configured interval):
1. Cleanup system runs automatically
2. Checks if transfer interval has passed
3. Transfers data to central location
4. Records transfer time in `AI\monitoring\last_transfer.json`

### On Central Computer:
1. Cleanup system collects data from employee folders
2. Moves data to `AI\training_data\`
3. Processes data for AI training
4. Runs Ollama training on combined dataset

## Quick Status Check

Run this anytime to check current status:
```batch
python _tools\config\CHECK_CONFIG_STATUS.py
```

This shows:
- Current mode (employee/central)
- Computer ID
- Central data path
- Transfer interval
- Path accessibility

