# Installation Troubleshooting Guide

## Common Installation Errors and Fixes

### NumPy Compilation Error (C++ Compiler Missing)

**Error:**
```
ERROR: Unknown compiler(s): [['icl'], ['cl'], ['cc'], ['gcc'], ['clang'], ['clang-cl'], ['pgcc']]
Could not find C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe
```

**Solution 1: Use Pre-built Wheels (Recommended)**
```cmd
python -m pip install --only-binary :all: numpy pandas opencv-python
```

**Solution 2: Install Visual Studio Build Tools**
1. Download Visual Studio Build Tools: https://visualstudio.microsoft.com/downloads/
2. Install "Desktop development with C++" workload
3. Run installer again

**Solution 3: Use Compatible Python Version**
- Install Python 3.10 or 3.11 (most packages have pre-built wheels)
- Avoid Python 3.13+ until packages catch up

**Quick Fix:**
Run `Installer\FIX_NUMPY_ERROR.bat` to install NumPy with pre-built wheels.

---

### OCR Dependencies (Tesseract/Poppler) Not Installed

**Symptoms:**
- Installation completes but OCR features don't work
- Bot can't process scanned PDFs
- No output from OCR installation step

**Solution 1: Run as Administrator**
1. Right-click `Installer\Install.bots`
2. Select "Run as Administrator"
3. Re-run installation

**Solution 2: Install Manually via winget**
```cmd
winget install -e --id UB-Mannheim.TesseractOCR
winget install -e --id Poppler.Poppler
```

**Solution 3: Run OCR Installer Separately**
```powershell
powershell -ExecutionPolicy Bypass -File "Installer\install_ocr_dependencies.ps1" -InstallDir "G:\Company\Software\_bots\Billing Department\Medisoft Billing"
```

**Solution 4: Download and Install Manually**
- Tesseract: https://github.com/tesseract-ocr/tesseract/wiki
- Poppler: https://github.com/oschwartz10612/poppler-windows/releases

---

### SQLite3 Installation Error

**Error:**
```
ERROR: Could not find a version that satisfies the requirement sqlite3
ERROR: No matching distribution found for sqlite3
```

**Solution:**
- `sqlite3` is a built-in Python module and shouldn't be in requirements.txt
- Remove `sqlite3` from any requirements files
- If needed, import it directly: `import sqlite3`

**Fix:**
Edit `_system\requirements_enterprise.txt` and remove the line with `sqlite3`.

---

### Python 3.14 Compatibility Issues

**Problem:**
- Many packages don't have pre-built wheels for Python 3.14 yet
- Packages try to compile from source, requiring C++ compiler
- Installation fails on systems without Visual Studio

**Solution:**
1. **Downgrade to Python 3.11** (Recommended)
   - Uninstall Python 3.14
   - Install Python 3.11 from https://www.python.org/
   - Make sure to check "Add Python to PATH"
   - Re-run installer

2. **Install Visual Studio Build Tools**
   - Allows packages to compile from source
   - See NumPy error solution above

3. **Wait for package updates**
   - Packages will add Python 3.14 support over time
   - Check package release notes for compatibility

---

### Installation Stops Early / OCR Step Never Runs

**Symptoms:**
- Installation stops after Python package installation
- OCR dependencies never install
- No output from step 5/5

**Solution:**
1. **Check error messages** - Look for failures in earlier steps
2. **Run Medisoft installer separately:**
   ```cmd
   cd "G:\Company\Software"
   Installer\Install.bots
   ```
3. **Check if INSTALL_BOTS.bat reached step 5** - May have failed earlier

---

### Missing Dependencies After Installation

**Symptoms:**
- Bot won't start
- Import errors when running bot
- "Module not found" errors

**Solution:**
1. **Verify installation completed:**
   ```cmd
   python -m pip list
   ```
2. **Re-install failed packages:**
   ```cmd
   python -m pip install --upgrade package_name
   ```
3. **Re-run installer** - Some packages may have failed silently

---

### Desktop Shortcut Not Created / Blank Icon

**Symptoms:**
- No shortcut on desktop after installation
- Shortcut exists but icon is blank

**Solution 1: Run as Administrator**
- Right-click installer → "Run as Administrator"

**Solution 2: Manually Create Shortcut**
```cmd
Installer\create_desktop_shortcut.vbs "G:\Company\Software\_bots\Billing Department\Medisoft Billing" "medisoft_billing_bot.bat"
```

**Solution 3: Fix Icon**
- Restart computer (refreshes icon cache)
- Or run: `ie4uinit.exe -show` in Command Prompt

---

## Complete Installation Checklist

After installation, verify:

- [ ] Python is installed and in PATH (`python --version`)
- [ ] Core packages installed (`python -m pip list | findstr pyautogui`)
- [ ] NumPy installed (`python -m pip list | findstr numpy`)
- [ ] Tesseract installed (`tesseract --version` or check `%TESSERACT_PATH%`)
- [ ] Poppler installed (`pdftoppm --version` or check `%POPPLER_PATH%`)
- [ ] Desktop shortcut created and has icon
- [ ] Bot can launch (`medisoft_billing_bot.bat`)

---

## Still Having Issues?

1. **Check installation log** - Save all output from installer
2. **Run installer with verbose output:**
   ```cmd
   Installer\Install.bots > installation_log.txt 2>&1
   ```
3. **Contact IT support** with:
   - Installation log file
   - Python version (`python --version`)
   - Windows version
   - Error messages

---

## Quick Fix Commands

**Fix NumPy:**
```cmd
Installer\FIX_NUMPY_ERROR.bat
```

**Install OCR dependencies only:**
```powershell
powershell -ExecutionPolicy Bypass -File "Installer\install_ocr_dependencies.ps1" -InstallDir "G:\Company\Software\_bots\Billing Department\Medisoft Billing"
```

**Re-run Medisoft installer:**
```cmd
Installer\Install.bots
```

**Check what's installed:**
```cmd
python -m pip list
tesseract --version
pdftoppm --version
```

