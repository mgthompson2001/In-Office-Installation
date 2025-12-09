# CCMD Bot Installation Guide
## Complete Setup Package for Employees

### Overview
This installation package contains all CCMD automation bots ready for deployment to employee computers. The installation process will:
- Install all required Python dependencies
- Create double-clickable batch wrappers for each bot
- Set up a desktop launcher icon
- Verify the installation is working correctly

### Quick Start
1. **Run the installer**: Double-click `INSTALL_BOTS.bat`
2. **Wait for completion**: The installer will install dependencies and create shortcuts
3. **Launch bots**: Use the desktop "Automation Hub" icon to launch any bot

### What's Included

#### Main Bots
- **Medical Records Bot**: Medical records management and processing
- **Consent Form Bot**: Consent forms with Penelope extraction (English/Spanish)
- **Welcome Letter Bot**: Generate and send welcome letters
- **Intake & Referral Department**: Access all intake and referral related bots
- **Billing Department**: Access all billing department automation tools
- **Penelope Workflow Tool**: Multi-purpose Penelope workflow automation

#### Department-Specific Bots
Located in sub-launchers:
- **Intake & Referral Department**: Referral processing bots
- **Billing Department**: Medisoft billing automation

### Installation Process

When employees run `INSTALL_BOTS.bat`, the system will:

1. **Check Python Version**: Ensures Python 3.8+ is installed
2. **Install Dependencies**: Installs all required packages from `requirements.txt`
3. **Create Batch Wrappers**: Creates .bat files for each bot so they can be double-clicked
4. **Create Desktop Icon**: Adds "Automation Hub" shortcut to desktop
5. **Verify Installation**: Tests that the launcher can start successfully

### Using the Bots

#### Option 1: Desktop Launcher (Recommended)
1. Double-click "Automation Hub" on your desktop
2. Select a bot from the list
3. Click "Launch Selected Bot"

#### Option 2: Direct Bot Access
Each bot can be double-clicked directly (look for .bat files):
- Navigate to the `_bots` folder
- Find the bot you want to run
- Double-click the .bat file (not the .py file)

### System Requirements

- **Python**: Version 3.8 or higher
- **Operating System**: Windows 10/11
- **Permissions**: Admin rights for initial installation
- **Internet**: Required for first-time dependency installation

### File Structure

```
In-Office Installation/
├── _bots/                      # All bot scripts
│   ├── Billing Department/
│   ├── Launcher/
│   ├── Med Rec/
│   ├── Penelope Workflow Tool/
│   ├── The Welcomed One, Exalted Rank/
│   └── Referral bot and bridge (final)/
├── _system/                    # Installation and system files
│   ├── secure_launcher.py      # Main launcher
│   ├── install_for_employee.py  # Installation script
│   ├── create_bat_wrappers.py  # Creates .bat files
│   ├── verify_installation.py  # Verification tool
│   └── requirements.txt        # Python dependencies
├── INSTALL_BOTS.bat            # Run this to install
└── INSTALLATION_GUIDE.md       # This file
```

### Troubleshooting

#### Bot Won't Launch
- Ensure Python 3.8+ is installed
- Run `INSTALL_BOTS.bat` again to reinstall dependencies
- Check that the bot file (.bat) exists in the bot's folder

#### Missing Dependencies
- Open Command Prompt in the installation folder
- Run: `python _system\install_for_employee.py`

#### Desktop Icon Not Working
- Right-click the "Automation Hub" shortcut
- Check "Start in" field is set to the installation directory
- Re-run `INSTALL_BOTS.bat` to recreate the shortcut

#### Verification
Run the verification tool:
```
python _system\verify_installation.py
```

This will check:
- Python version
- Dependencies installed
- Bot files exist
- Batch wrappers created
- Desktop shortcut exists
- Launcher works properly

### For IT/Administrators

#### Deployment to Multiple Computers
1. Copy the entire "In-Office Installation" folder to each computer
2. Run `INSTALL_BOTS.bat` on each machine
3. The installation is per-user; each employee must run it

#### Updating Bots
1. Update bot files in the `_bots` folder
2. Run `python _system\create_bat_wrappers.py` to recreate wrappers
3. Employees can re-run `INSTALL_BOTS.bat` to update their setup

#### Customization
- **Change launcher icon**: Replace `_system\ccmd_bot_icon.ico`
- **Modify launcher**: Edit `_system\secure_launcher.py`
- **Add new bots**: Add to `_bots` folder, rerun `create_bat_wrappers.py`

### Security Notes

The launcher is password-protected for code access:
- **Password**: `Integritycode1!`
- This prevents employees from viewing/editing bot code
- Code access is logged and monitored
- 30-minute timeout for security

### Support

For issues or questions:
1. Run the verification tool: `python _system\verify_installation.py`
2. Check the installation log
3. Contact IT support with error messages

### Version History

- **2025-10-28**: Complete rewrite with batch wrappers and improved installation
- Enhanced desktop shortcut creation
- Added comprehensive verification system
- Fixed bot path issues

---

**Ready to Install?** Double-click `INSTALL_BOTS.bat` to begin!

