# Installation Testing Checklist

## ⚠️ IMPORTANT: Testing Required

The installer has been updated with automatic Python installation, but **it needs to be tested** on a real machine (especially one with Python 3.14) before deploying to employees.

## Pre-Deployment Testing Steps

### 1. Test on a Clean Machine (Recommended)

Test on a machine that:
- Has Python 3.14 installed (the problematic version)
- OR has no Python installed
- OR has Python 3.11 installed (should work immediately)

### 2. Test Script Available

Run the test script first to verify all components:
```cmd
Installer\test_installer.bat
```

This will check:
- ✅ All required scripts are present
- ✅ Python version check logic
- ✅ PowerShell execution policy
- ✅ Path verification

### 3. Full Installation Test

Run the full installer:
```cmd
INSTALL_BOTS.bat
```

Monitor for these issues:

#### ✅ Python Installation
- [ ] Python 3.14 detected correctly
- [ ] Python 3.11 installation starts automatically
- [ ] Python 3.11 installs successfully
- [ ] PATH is refreshed after installation
- [ ] Installer continues after Python installation

#### ✅ Python Dependencies
- [ ] NumPy installs with pre-built wheels (no compilation)
- [ ] All packages from requirements.txt install
- [ ] No compilation errors for packages that have wheels

#### ✅ OCR Dependencies
- [ ] Tesseract OCR installs (via winget or download)
- [ ] Poppler installs (via winget or download)
- [ ] Environment variables set correctly
- [ ] Both tools can be found after installation

#### ✅ Desktop Shortcut
- [ ] Shortcut created on desktop
- [ ] Icon appears correctly (not blank)
- [ ] Shortcut launches bot correctly

#### ✅ Data Migration
- [ ] Saved selectors migrate (if any exist)
- [ ] User credentials migrate (if any exist)

### 4. Common Issues to Watch For

#### Issue: Python PATH Not Refreshed
**Symptoms:** Python installed but not found after installation
**Solution:** The installer tries multiple methods to refresh PATH. If it fails, user may need to restart terminal.

#### Issue: NumPy Still Tries to Compile
**Symptoms:** NumPy compilation error even with Python 3.11
**Cause:** Package version in requirements.txt requires compilation
**Solution:** Use `--only-binary :all:` flag (already in installer)

#### Issue: OCR Installation Fails
**Symptoms:** Tesseract/Poppler not installed
**Cause:** Requires Administrator rights or network issue
**Solution:** Run installer as Administrator, or install manually

#### Issue: Desktop Shortcut Icon Blank
**Symptoms:** Shortcut created but icon is blank
**Cause:** Icon file not found or not accessible
**Solution:** Restart computer (refreshes icon cache)

### 5. Post-Installation Verification

After installation completes, verify:

```cmd
REM Check Python version
python --version
REM Should show: Python 3.11.x

REM Check NumPy installed
python -c "import numpy; print(numpy.__version__)"
REM Should show version number

REM Check Tesseract
tesseract --version
REM Should show version if installed

REM Check Poppler
pdftoppm -v
REM Should show version if installed

REM Check desktop shortcut
REM Look for "Medisoft Billing Bot" on desktop
```

### 6. Test on Employee's Computer

Before deploying:
1. **Backup current installation** (if exists)
2. **Note current Python version**: `python --version`
3. **Run test script**: `Installer\test_installer.bat`
4. **Run full installer**: `INSTALL_BOTS.bat`
5. **Monitor output** for any errors
6. **Test bot launch** after installation

### 7. Rollback Plan

If installation fails:
1. **Uninstall Python 3.11** (if installed automatically)
2. **Restore previous Python** (if backup exists)
3. **Check logs** in installation output
4. **Run troubleshooting**: `Installer\TROUBLESHOOTING.md`

## Testing on Employee's Computer (G:\Company\Software\)

Since we have a log from a failed installation at `G:\Company\Software\`, you can:

1. **Test the fix directly there:**
   ```cmd
   cd "G:\Company\Software"
   INSTALL_BOTS.bat
   ```

2. **Monitor the output** and watch for:
   - Python 3.14 detection
   - Automatic Python 3.11 installation
   - Successful continuation after Python installation
   - OCR dependencies installation

3. **If it works**, you're good to deploy
4. **If it fails**, check the output and fix any issues

## What Was Fixed (Summary)

1. ✅ **Python 3.14 detection** - Installer now detects and handles it
2. ✅ **Automatic Python 3.11 installation** - Installs before other steps
3. ✅ **NumPy pre-built wheels** - Avoids compilation errors
4. ✅ **OCR installation always runs** - Even if Python packages have issues
5. ✅ **Better error handling** - Clear messages and fallbacks

## Known Limitations

1. **PATH refresh** - May require terminal restart in some cases
2. **Administrator rights** - OCR installation may need admin rights
3. **Network required** - Python download requires internet
4. **Python 3.14** - If employee manually reinstalls it after, same issue will occur

## Recommendations

1. **Test on one employee's computer first** (like G:\Company\Software)
2. **If successful**, deploy to other employees
3. **If issues found**, fix and retest before full deployment
4. **Document any new issues** found during testing

---

**Status**: Ready for testing, but **not yet deployed**. Test first!

