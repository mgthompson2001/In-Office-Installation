# Installer Integration Notes

## Integration with Main INSTALL_BOTS.bat

This installer can be integrated with the main `INSTALL_BOTS.bat` script at:
```
C:\Users\...\Desktop\In-Office Installation\INSTALL_BOTS.bat
```

### Recommended Integration

Add this section to `INSTALL_BOTS.bat` after the main installation:

```batch
REM ==========================================
REM Medisoft Billing Bot Installation
REM ==========================================
echo.
echo Installing Medisoft Billing Bot...
set "MEDISOFT_INSTALLER=%~dp0_bots\Billing Department\Medisoft Billing\Installer\Install.bots"
if exist "%MEDISOFT_INSTALLER%" (
    echo Running Medisoft Billing Bot installer...
    call "%MEDISOFT_INSTALLER%"
    if errorlevel 1 (
        echo [WARNING] Medisoft Billing Bot installation encountered issues
        echo The bot may still work, but some features may be limited
    ) else (
        echo [OK] Medisoft Billing Bot installation complete
    )
) else (
    echo [SKIP] Medisoft Billing Bot installer not found
)
```

### Standalone Usage

The installer can also be run standalone:
1. Navigate to the `Installer` folder
2. Double-click `Install.bots`
3. Follow the prompts

## Differences from Old install.bat

The new installer (`Install.bots`) is more robust than the old `install.bat`:

1. **Flexible Python Detection**
   - Checks multiple Python commands
   - Searches common installation locations
   - Doesn't fail if Python is in non-standard location

2. **Complete OCR Setup**
   - Automatically installs Tesseract and Poppler
   - Uses winget when available
   - Downloads portable versions as fallback
   - Sets environment variables correctly

3. **Icon Management**
   - Automatically locates and sets up the red I icon
   - Converts PNG to ICO format when needed
   - Handles icon fallbacks gracefully

4. **Data Migration**
   - Automatically migrates saved selectors
   - Migrates user credentials
   - Copies saved images
   - Merges data from old installations

5. **Path Configuration**
   - Configures all paths automatically
   - Creates configuration file
   - Sets up vendor directory

6. **Desktop Shortcut**
   - Creates shortcut with proper icon
   - Sets working directory correctly
   - Configures target properly

## Backward Compatibility

The old `install.bat` file is still present in the root directory for backward compatibility. However, the new `Install.bots` installer is recommended for:

- New installations
- Reinstalling on employee computers
- Fixing installation issues
- Updating dependencies

## Migration Path

When deploying to existing installations:

1. **Option A: Full Reinstallation** (Recommended)
   - Run `Installer\Install.bots`
   - This will migrate data automatically
   - Ensures all dependencies are up to date

2. **Option B: Update Only**
   - Keep existing installation
   - Run `Installer\Install.bots` to update dependencies
   - Data migration will merge with existing data

3. **Option C: Manual Update**
   - Update dependencies manually: `pip install -r requirements.txt`
   - Run OCR installer: `Installer\install_ocr_dependencies.ps1`
   - Manually create desktop shortcut if needed

## Testing Checklist

Before deploying to employees, test:

- [ ] Python detection works with different Python installations
- [ ] All dependencies install correctly
- [ ] OCR dependencies install (Tesseract, Poppler)
- [ ] Desktop shortcut is created
- [ ] Icon appears correctly (not blank)
- [ ] Shortcut launches bot correctly
- [ ] Saved selectors migrate correctly
- [ ] Bot works with migrated data
- [ ] Bot saves new data to correct location

## Known Issues and Workarounds

1. **Blank Icon**
   - **Cause**: Icon file not found or not accessible
   - **Fix**: Run `Installer\setup_icon.py` manually, restart computer

2. **Python Not Found**
   - **Cause**: Python not in PATH or non-standard installation
   - **Fix**: Install Python with "Add to PATH" or specify Python path in installer

3. **OCR Dependencies Fail**
   - **Cause**: Requires Administrator rights for system installation
   - **Fix**: Run installer as Administrator, or uses vendor directory installation

4. **Shortcut Opens Blank**
   - **Cause**: Working directory or target path incorrect
   - **Fix**: Verify `medisoft_billing_bot.bat` exists and Python is in PATH

## Future Improvements

Potential enhancements for future versions:

1. **Silent Installation Mode**
   - Command-line flags for silent installation
   - Progress logging to file
   - Error reporting to log file

2. **Update Checker**
   - Check for new installer versions
   - Auto-update dependencies
   - Notify users of updates

3. **Uninstaller**
   - Clean uninstall script
   - Remove dependencies option
   - Backup user data before uninstall

4. **Installation Verification**
   - Post-installation verification script
   - Test all bot features
   - Generate installation report

