# Medisoft Billing Bot - Installation Guide

## Quick Start Installation

### Option 1: Automated Installation (Recommended)
1. Double-click **`install.bat`** to automatically install all dependencies
2. The script will check Python, upgrade pip, and install all packages
3. Wait for completion (may take 2-5 minutes)
4. Run the bot by double-clicking **`medisoft_billing_bot.py`**

### Option 2: Manual Installation
1. Open Command Prompt (cmd) or PowerShell
2. Navigate to the bot directory:
   ```cmd
   cd "C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\_bots\Billing Department\Medisoft Billing"
   ```
3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

---

## Prerequisites

### Python 3.7 or Higher
- **Check if installed**: Open Command Prompt and type `python --version`
- **If not installed**: Download from https://www.python.org/
  - **Important**: During installation, check ✅ **"Add Python to PATH"**
  - Recommended: Install Python 3.10 or 3.11 for best compatibility

---

## Required Dependencies

The bot requires these packages (installed automatically by `install.bat`):

| Package | Purpose | Required |
|---------|---------|----------|
| **pyautogui** | GUI automation (mouse/keyboard control) | ✅ Yes |
| **pywinauto** | Windows UI element detection | ✅ Yes |
| **Pillow** | Image processing for screenshots | ✅ Yes |
| **keyboard** | F8/F9 hotkeys for training | ⚠️ Recommended |
| **opencv-python** | Better image recognition (confidence matching) | ⚠️ Optional |

---

## Installation Troubleshooting

### Issue: "Python is not recognized"
**Solution**: Python is not in your system PATH
1. Reinstall Python from https://www.python.org/
2. Make sure to check ✅ **"Add Python to PATH"** during installation
3. Restart your computer after installation

### Issue: "pip is not recognized"
**Solution**: pip needs to be in PATH
1. Try: `python -m pip install -r requirements.txt`
2. Or reinstall Python with "Add Python to PATH" checked

### Issue: OpenCV installation fails
**Solution**: OpenCV is **optional** - the bot works without it!
- The bot will use exact image matching instead of confidence-based matching
- Image recognition will still work, just less flexible
- This is **not a critical error** - you can continue using the bot

### Issue: Keyboard module installation fails
**Solution**: Try installing separately
```cmd
pip install keyboard
```
- If this fails, the bot will still work, but F8/F9 hotkeys won't function
- You can still use the bot normally

### Issue: Permission errors during installation
**Solution**: Run Command Prompt as Administrator
1. Right-click Command Prompt → "Run as Administrator"
2. Navigate to the bot directory
3. Run: `pip install -r requirements.txt`

---

## Post-Installation

### Verify Installation
1. Open Command Prompt in the bot directory
2. Run: `python medisoft_billing_bot.py`
3. If the GUI opens, installation was successful!

### First Time Setup
1. Click **"Add User"** to create your user profile
2. Enter your Medisoft username and password
3. Your credentials will be saved securely for future use
4. Click **"Login"** to start using the bot

---

## Updating Dependencies

If you need to update packages later:
```cmd
pip install --upgrade -r requirements.txt
```

---

## System Requirements

- **OS**: Windows 10/11 (64-bit recommended)
- **Python**: 3.7 or higher (3.10+ recommended)
- **RAM**: 4GB minimum, 8GB recommended
- **Display**: 1920x1080 or higher recommended (for screenshot recognition)
- **Medisoft**: Medisoft installation required (separate from bot)

---

## Getting Help

If you encounter issues:
1. Check the **Activity Log** in the bot's GUI for error messages
2. Review this installation guide
3. Contact IT support with the error message from the Activity Log

---

## Security Notes

- User credentials are stored locally in `medisoft_users.json`
- Credentials are encrypted using Python's standard library
- Never share your `medisoft_users.json` file
- Each user should maintain their own installation

