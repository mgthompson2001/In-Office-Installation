# Quick Start Guide - Medisoft Billing Bot Installation

## For Employees (Simple Installation)

1. **Double-click `Install.bots`** in the Installer folder
2. Wait for installation to complete (2-5 minutes)
3. Look for **"Medisoft Billing Bot"** shortcut on your desktop
4. **Double-click the shortcut** to launch the bot

That's it! The installer handles everything automatically.

## What Gets Installed

- ✅ Python dependencies (all required packages)
- ✅ OCR dependencies (Tesseract, Poppler) for PDF processing
- ✅ Desktop shortcut with red I icon
- ✅ All paths configured automatically
- ✅ Saved selectors migrated (if upgrading from old installation)

## Troubleshooting Quick Fixes

### Shortcut Icon is Blank

**Quick fix:**
1. Right-click the shortcut → Properties
2. Click "Change Icon"
3. Browse to: `Installer\medisoft_bot_icon.ico` or `.png`
4. Click OK

**Or:** Restart your computer (this refreshes the icon cache)

### Bot Won't Start

**Quick fix:**
1. Make sure Python is installed: Open Command Prompt, type `python --version`
2. If Python is not found, install from https://www.python.org/
3. Make sure to check "Add Python to PATH" during installation
4. Run `Install.bots` again

### Saved Selectors Don't Work

**Quick fix:**
1. Use the bot's training tools:
   - **F9** = Record coordinates
   - **F8** = Capture screenshot
2. Reconfigure any missing selectors

## Need Help?

- See full documentation: `README.md` in this folder
- See troubleshooting: `../INSTALLATION_GUIDE.md`
- Contact IT support with error messages

