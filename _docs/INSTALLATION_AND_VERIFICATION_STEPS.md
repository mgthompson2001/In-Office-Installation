# Installation and Verification Steps

## For Employees: Step-by-Step Guide

### Step 1: Install the System
1. Double-click **`INSTALL_BOTS.bat`**
2. Follow the prompts:
   - It will install Python dependencies
   - It will ask for the **central data folder path** (e.g., `G:\Company\Software\Training Data`)
   - It will configure employee mode automatically
3. Wait for installation to complete

### Step 2: Verify Installation (IMPORTANT!)
**After installation completes**, run this to verify everything is working:

```batch
python _tools\config\VERIFY_EMPLOYEE_INSTALLATION.py
```

### What You Should See

**✅ If everything worked:**
```
✅ Employee mode is configured
✅ Central data folder exists
✅ Passive cleanup system is installed
✅ Data collection setup is correct
✅ Bot integration is configured
✅ Can write to central data folder
```

**⚠️ If something needs fixing:**
The script will tell you exactly what to do, for example:
- "Mode: NOT SET" → Run configuration script
- "Cannot write to central data folder" → Check network/permissions

## Timeline

```
1. Run INSTALL_BOTS.bat
   ↓
2. Installation completes
   ↓
3. Run VERIFY_EMPLOYEE_INSTALLATION.py
   ↓
4. Check results
   ↓
5. If all ✅, you're done!
   If ⚠️, follow the instructions shown
```

## Quick Reference

- **Installation**: `INSTALL_BOTS.bat` (run first)
- **Verification**: `python _tools\config\VERIFY_EMPLOYEE_INSTALLATION.py` (run after)
- **Re-configure**: `python _tools\config\CONFIGURE_EMPLOYEE_MODE.py` (if needed)

## For IT/Admin

After employees install and verify:
1. Check central data folder: `G:\Company\Software\Training Data\`
2. You should see folders appearing for each employee computer
3. Data will transfer automatically every 24 hours (or configured interval)

