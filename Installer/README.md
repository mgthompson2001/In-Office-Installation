# Medisoft Billing Bot - Installer Documentation

This folder contains all installation components for the Medisoft Billing Bot. The installer is designed to be consumer-ready and handles all dependencies, configurations, and setup automatically.

## Quick Start

**For end users:**
1. Double-click `Install.bots` in this folder
2. Follow the prompts
3. Look for "Medisoft Billing Bot" shortcut on your desktop
4. Double-click the shortcut to launch the bot

**For IT/Administrators:**
- See the main installation guide: `../INSTALLATION_GUIDE.md`
- This installer can also be called from the main `INSTALL_BOTS.bat` script

## Installer Components

### Main Installer
- **`Install.bots`** - Main installation batch script that orchestrates all installation steps

### Supporting Scripts

1. **`install_ocr_dependencies.ps1`**
   - Installs Tesseract OCR and Poppler for PDF processing
   - Uses winget when available, falls back to direct download
   - Installs to vendor directory or standard system locations

2. **`create_desktop_shortcut.vbs`**
   - Creates desktop shortcut with proper icon
   - Handles icon location detection (red I icon)
   - Configures working directory and target correctly

3. **`configure_paths.py`**
   - Updates paths in bot files to match installation location
   - Creates configuration file with installation paths
   - Ensures vendor directory exists

4. **`migrate_saved_data.py`**
   - Migrates saved selectors, coordinates, and user data
   - Merges data from old installations
   - Copies image files (saved selectors)

5. **`setup_icon.py`**
   - Locates and sets up the red I icon for desktop shortcut
   - Converts PNG to ICO format when needed
   - Handles icon fallbacks

## Installation Steps

The installer performs these steps in order:

1. **Python Detection** (Flexible)
   - Checks for Python in PATH
   - Tries multiple Python commands (python, python3, py)
   - Checks common installation locations
   - **Important**: Does not require Python to be installed first (but Python is needed for bot to run)

2. **Pip Upgrade**
   - Upgrades pip to latest version
   - Ensures package installation works correctly

3. **Python Dependencies**
   - Installs all packages from `requirements.txt`
   - Installs core dependencies first
   - Handles failures gracefully

4. **OCR Dependencies**
   - Installs Tesseract OCR (for text recognition)
   - Installs Poppler (for PDF to image conversion)
   - Uses winget when available, downloads portable versions as fallback

5. **Icon Setup**
   - Locates the red I icon
   - Converts to ICO format if needed
   - Sets up icon for desktop shortcut

6. **Path Configuration**
   - Updates paths in bot files
   - Creates configuration file
   - Sets up vendor directory

7. **Data Migration**
   - Migrates saved selectors and coordinates
   - Copies user data files
   - Merges data from old installations

8. **Desktop Shortcut Creation**
   - Creates shortcut on desktop
   - Configures icon correctly
   - Sets working directory

## Icon Setup

The installer looks for the icon in these locations (in order):

1. `Installer/medisoft_bot_icon.ico`
2. `Installer/medisoft_bot_icon.png`
3. `Installer/icon.ico`
4. `../../_admin/ccmd_bot_icon.png` (shared icon)
5. Default Python/system icon (fallback)

### Fixing Blank Icon Issue

If the desktop shortcut shows a blank icon:

1. **Ensure icon file exists:**
   - Check that `Installer/medisoft_bot_icon.ico` or `.png` exists
   - Or that `../../_admin/ccmd_bot_icon.png` is accessible

2. **Run icon setup manually:**
   ```cmd
   python Installer\setup_icon.py
   ```

3. **Recreate shortcut:**
   ```cmd
   cscript Installer\create_desktop_shortcut.vbs "installation_path" "medisoft_billing_bot.bat"
   ```

4. **Refresh icon cache (if needed):**
   - Restart Windows Explorer or reboot computer
   - Run: `ie4uinit.exe -show` in Command Prompt

## Troubleshooting

### Installation Fails

**Python not found:**
- Install Python 3.7+ from https://www.python.org/
- Make sure to check "Add Python to PATH" during installation
- Or continue installation if Python is installed but not in PATH

**Pip installation fails:**
- Check internet connection
- Try running as Administrator
- Verify Python is installed correctly

**OCR dependencies fail:**
- This is not critical - bot will work but scanned PDF processing may be limited
- Try running OCR installer manually: `powershell -ExecutionPolicy Bypass -File Installer\install_ocr_dependencies.ps1`

### Shortcut Issues

**Shortcut not created:**
- Check desktop permissions
- Try running installer as Administrator
- Create shortcut manually using `create_desktop_shortcut.vbs`

**Icon is blank:**
- See "Fixing Blank Icon Issue" above
- Ensure icon file exists and is accessible
- Try restarting computer

**Shortcut opens blank page:**
- Verify `medisoft_billing_bot.bat` exists
- Check that Python is in PATH
- Verify working directory is set correctly in shortcut properties

### Data Migration Issues

**Saved selectors not transferred:**
- Check if old installation had data files
- Use bot's training tools (F8/F9) to reconfigure selectors
- Manually copy JSON files if needed

**User data not migrated:**
- Check old installation locations:
  - Desktop/Medisoft Billing
  - Documents/Medisoft Billing
  - Downloads/Medisoft Billing
- Manually copy `medisoft_users.json` if needed

## File Locations

After installation, these files are created/updated:

```
Medisoft Billing/
├── vendor/                          # OCR dependencies (if installed locally)
│   ├── Tesseract-OCR/
│   └── poppler/
├── medisoft_users.json              # User credentials
├── medisoft_coordinates.json        # Saved coordinates
├── *.png                            # Saved selector images
└── Installer/
    ├── install_config.json          # Installation configuration
    └── medisoft_bot_icon.ico        # Desktop shortcut icon
```

## Advanced Usage

### Silent Installation

For automated deployments, you can run the installer with minimal prompts:

```cmd
echo y | Install.bots
```

### Custom Installation Directory

The installer automatically detects its location and uses the parent directory as the installation directory. To install to a different location:

1. Copy the entire bot folder to desired location
2. Run `Installer\Install.bots` from that location

### Integration with Main Installer

This installer can be called from the main `INSTALL_BOTS.bat` script:

```batch
call "%~dp0_bots\Billing Department\Medisoft Billing\Installer\Install.bots"
```

## Requirements

- **Windows 10/11** (64-bit recommended)
- **Python 3.7+** (detected automatically)
- **Internet connection** (for downloading dependencies)
- **Administrator rights** (optional, but recommended for OCR dependencies)

## Support

For installation issues:
1. Check this README
2. Review `../INSTALLATION_GUIDE.md`
3. Check installation log in console output
4. Contact IT support with error messages

## Version History

- **v1.0** - Initial consumer-ready installer
  - Flexible Python detection
  - Automatic OCR dependency installation
  - Icon setup and desktop shortcut creation
  - Data migration support

