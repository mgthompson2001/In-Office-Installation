# CCMD Bot Installation Instructions

## For Employees

### Quick Installation
1. **Double-click `INSTALL_BOTS.bat`** in this folder
2. Follow the on-screen instructions
3. Look for "CCMD Automation Hub" icon on your desktop
4. Double-click the desktop icon to launch

### If Installation Fails
1. **Double-click `TROUBLESHOOT.bat`** to diagnose issues
2. Check the error messages and follow the suggested fixes
3. Contact IT support if problems persist

### Manual Installation (if needed)
1. Open Command Prompt as Administrator
2. Navigate to this folder: `cd "C:\path\to\In-Office Installation"`
3. Run: `python _system\install_for_employee.py`

## What Gets Installed
- **Desktop Shortcut**: "Automation Hub" with proper red icon
- **Python Packages**: All required dependencies
- **Bot Software**: Access to all automation tools

## Troubleshooting Common Issues

### "Blank White Icon" Problem
- **Cause**: Hardcoded paths in old installation script
- **Fix**: Use the new `INSTALL_BOTS.bat` file
- **Result**: Proper red "I" icon should appear

### "Launcher Closes Immediately" Problem
- **Cause**: Missing dependencies or path issues
- **Fix**: Run `TROUBLESHOOT.bat` to identify the issue
- **Common Solutions**:
  - Install missing Python packages
  - Check that all files are present
  - Verify Python 3.8+ is installed

### "Python Not Found" Error
- **Cause**: Python not installed or not in PATH
- **Fix**: Install Python 3.8+ from python.org
- **Note**: Make sure to check "Add Python to PATH" during installation

## File Structure
```
In-Office Installation/
├── INSTALL_BOTS.bat          ← Double-click this to install
├── TROUBLESHOOT.bat          ← Double-click this if problems occur
├── _system/
│   ├── secure_launcher.py    ← Main launcher (don't run directly)
│   ├── install_for_employee.py ← New installation script
│   ├── troubleshoot_launcher.py ← Diagnostic tool
│   └── ccmd_bot_icon.ico     ← Red "I" icon file
└── _bots/                    ← Bot software (don't modify)
```

## Support
If you continue to have issues:
1. Run the troubleshooter first
2. Note the specific error messages
3. Contact IT support with the error details
