# CCMD Bot Master - Simple Installation Guide

## 🚀 How to Install on Any Computer

### Step 1: Copy This Folder
- Copy the entire "In-Office Installation" folder to the target computer
- Put it on the Desktop or in Documents folder

### Step 2: Install Everything
- **Double-click `install.bat`** (the easiest way)
- OR open Command Prompt and run: `python install_bots.py`
- **Automatic Registration**: Your computer is automatically added to the update system

### Step 3: Use the Bots
- Look for "CCMD Bot Launcher" on the desktop (with red pillar "I" icon)
- Double-click it to start
- Select your bot from the dropdown menu
- Click "Launch Selected"
- **Note**: Password is only required for IT personnel to access bot code

## 🎯 For Non-Technical Users (No Coding Required)

### Easy Update Management
- **Double-click `easy_update_manager.py`** to open the Easy Update Manager
- **No coding knowledge required** - everything is click-and-go
- **Clear instructions** in each tab of the interface
- **Step-by-step guidance** for all tasks

### What You Can Do:
- ✅ **Add computers** to the update system
- ✅ **Create update packages** for bug fixes and new features
- ✅ **Deploy updates** to all computers at once
- ✅ **Monitor status** of all computers
- ✅ **Troubleshoot problems** with built-in help

### Quick Start for Updates:
1. **Open Easy Update Manager** (`easy_update_manager.py`)
2. **Add computers** in the "📋 Manage Computers" tab
3. **Create updates** in the "📦 Create Updates" tab

## 🌐 Centralized Computer Management

**IMPORTANT**: By default, each computer only sees itself in the update manager. To see all computers from one location:

### Option 1: Network Server (Recommended)
1. Create a shared folder on your server: `\\YOUR_SERVER\CCMD_Bot_Manager`
2. Give all users read/write access to this folder
3. Restart the update manager on all computers
4. All computers will now appear in the centralized list

### Option 2: Local Shared Folder
1. Run `setup_centralized_management.bat` for guided setup
2. Or manually create `C:\CCMD_Bot_Manager` and share it
3. Give all users full access permissions

### Option 3: Use Existing Network Share
- Point to your existing shared folder
- Ensure all computers can read/write to it

**Note**: The update manager automatically detects and uses centralized locations when available.
4. **Deploy updates** in the "🚀 Deploy Updates" tab
5. **Monitor status** in the "📊 Monitor Status" tab

---

## 📋 What You Need Before Installing

### Required Software:
- **Python 3.8 or higher** - [Download from python.org](https://python.org)
- **Google Chrome Browser** - [Download from chrome.google.com](https://chrome.google.com)

### Required Access:
- **Internet connection**
- **Login credentials** for Penelope and TherapyNotes systems

---

## 🤖 Available Bots

### Main Launcher
- **Medical Records Bot** - Process medical records
- **Consent Form Bot** - Generate and upload consent forms  
- **Welcome Letter Bot** - Create welcome letters
- **Intake & Referral Department** - Access to all intake/referral bots

### Intake & Referral Department
- **Remove Counselor Bot** - Remove counselor assignments
- **Unified Launcher** - Run Counselor Assignment + Intake & Referral bots together
- **Referral Form/Upload Bot** - Standalone referral processing
- **Counselor Assignment Bot** - Assign counselors to clients

---

## 🔧 Troubleshooting

### "Python not found" Error
- Install Python 3.8+ from python.org
- Make sure to check "Add Python to PATH" during installation

### "Chrome not found" Warning
- Install Google Chrome browser from chrome.google.com

### Bot won't start
- Make sure all files are in the correct folder
- Check that Python and Chrome are installed
- Verify internet connection is working

### Need Help?
- Check the bot's log output in the GUI window
- Verify login credentials are correct
- Contact IT support with specific error messages

---

## 🔒 Security Features

### Password Protection
- **Code Access Password**: `Integritycode1!` (IT personnel only)
- **Session Timeout**: 30 minutes of inactivity for code access
- **Max Attempts**: 3 failed attempts will lock code access
- **Code Protection**: Bot code is encrypted to prevent unauthorized viewing/editing
- **Employee Access**: No password required for normal bot usage

### For IT Administrators
- Use `encrypt_code.py` to encrypt bot files
- Original files are backed up in `encrypted_backup` folder
- Only authorized personnel should have access to the encryption tool

---

## 📁 What's in This Folder

```
In-Office Installation/
├── Launcher/
│   ├── bot_launcher.py              # Main launcher
│   └── intake_referral_launcher.py  # Department launcher
├── Referral bot and bridge (final)/
│   ├── counselor_assignment_bot.py
│   └── isws_Intake_referral_bot_REFERENCE_PLUS_PRINT_ONLY_WITH_LOOPBACK_LOOPONLY_SCROLLING_TINYLOG_NO_BOTTOM_UPLOADER.py
├── The Welcomed One, Exalted Rank/
│   ├── integrity_consent_bot.py
│   └── isws_welcome_DEEPFIX2_NOTEFORCE_v14.py
├── Med Rec/
├── Cursor versions/
├── File Templates/
├── secure_launcher.py               # Password-protected launcher
├── easy_update_manager.py           # Easy update management (no coding required)
├── encrypt_code.py                  # Code encryption tool (IT only)
├── requirements.txt                  # Python dependencies
├── install_bots.py                   # Installation script
├── install.bat                       # Easy installer (double-click)
├── NON_TECHNICAL_GUIDE.md           # Guide for non-technical users
└── README.md                         # This file
```

---

## ✅ Quick Test

After installation:
1. Double-click "CCMD Bot Launcher" on desktop
2. Select "Intake & Referral Department" from dropdown
3. Click "Launch Selected"
4. Confirm the department launcher opens
5. Close it (you don't need to run a bot yet)

If this works, your installation is successful!

## 🔄 Automatic Computer Registration

When you install the bot software:
- **Your computer is automatically registered** in the update system
- **No manual setup required** - computer name, IP address, and bot path are captured
- **Ready for updates** - you'll receive automatic update notifications
- **IT can see your computer** in the update manager without manual entry

This means when IT creates updates, your computer is automatically included in the deployment list!

---

*For technical support, contact your IT department.*
