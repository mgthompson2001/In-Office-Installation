# Medisoft Billing Bot

Automated bot for streamlining Medisoft billing workflows. This bot handles login and navigation tasks to save time and reduce errors.

---

## 🚀 Quick Start

### For New Users:
1. **Install dependencies**: Double-click **`install.bat`**
2. **Run the bot**: Double-click **`medisoft_billing_bot.py`**
3. **Add your credentials**: Click "Add User" and enter your Medisoft login
4. **Start using**: Click "Login" to begin

### For IT/SysAdmins:
See **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** for detailed setup instructions and troubleshooting.

---

## ✨ Features

- **Secure Login**: Save and manage user credentials locally
- **Automated Navigation**: Navigate to Reports and other Medisoft sections automatically
- **Coordinate Training**: Record precise coordinates for any UI element (F9 hotkey)
- **Image Recognition**: Capture screenshots for button recognition (F8 hotkey)
- **Activity Logging**: Real-time log of all bot activities
- **Multi-User Support**: Each employee can save their own credentials

---

## 📋 Requirements

- Windows 10/11
- Python 3.7+ (installation guide included)
- Medisoft installed on the computer
- Internet connection (for initial dependency installation)

---

## 📦 Installation Files

- **`install.bat`** - Automated installation script (double-click to run)
- **`requirements.txt`** - Python package dependencies
- **`medisoft_billing_bot.py`** - Main bot application
- **`INSTALLATION_GUIDE.md`** - Detailed installation and troubleshooting guide

---

## 🎮 Usage

### Login:
1. Select your name from the dropdown, or click "Add User" to create a profile
2. Enter your Medisoft username and password
3. Click "Login"

### Navigate to Reports:
1. After logging in, click "Navigate to Reports"
2. The bot will automatically find and click the "Launch Medisoft Reports" button

### Training the Bot (Coordinate Capture):
1. Enter an element name (e.g., "Reports Button")
2. Click "Enable F9" 
3. Hover your mouse over the element in Medisoft
4. Press **F9** to capture the position
5. The coordinate is saved automatically

### Training the Bot (Screenshot Capture):
1. Enter an element name (e.g., "Launch Medisoft Reports")
2. Click "Enable F8"
3. Hover your mouse over the element in Medisoft  
4. Press **F8** to capture a screenshot
5. The image is saved and will be used for recognition

---

## 🔧 Keyboard Shortcuts

- **F9**: Record mouse position (coordinates)
- **F8**: Capture screenshot for image recognition

*Note: Requires `keyboard` module installed (included in install.bat)*

---

## 📁 File Structure

```
Medisoft Billing/
├── medisoft_billing_bot.py    # Main application
├── install.bat                 # Installation script
├── requirements.txt            # Dependencies list
├── README.md                   # This file
├── INSTALLATION_GUIDE.md       # Detailed setup guide
├── medisoft_users.json         # Saved user credentials (auto-created)
├── medisoft_coordinates.json   # Saved coordinates (auto-created)
└── *.png                       # Screenshot images for recognition
```

---

## 🛡️ Security

- All credentials are stored **locally** on your computer
- Credentials are saved in `medisoft_users.json` (plain text - keep secure!)
- Never share your `medisoft_users.json` file
- Each user maintains their own installation

---

## ⚠️ Troubleshooting

**Bot won't start?**
- Run `install.bat` to ensure all dependencies are installed
- Check that Python is installed: Open Command Prompt, type `python --version`

**Can't find buttons?**
- Use the Coordinate Training Tool (F9) or Screenshot Capture (F8)
- Check the Activity Log for error messages

**Hotkeys not working?**
- Make sure `keyboard` module is installed: `pip install keyboard`
- Restart the bot after installing

**Need more help?**
- See **INSTALLATION_GUIDE.md** for detailed troubleshooting
- Check the Activity Log in the bot's GUI for specific error messages

---

## 📝 Notes

- The bot requires Medisoft to be installed on the same computer
- Screen resolution changes may affect coordinate-based clicking
- Image recognition works across different screen sizes
- The bot logs all activities - check the Activity Log section for details

---

## 👥 Support

For technical support or questions:
1. Review the Activity Log in the bot's GUI
2. Check INSTALLATION_GUIDE.md for common issues
3. Contact IT support with specific error messages

---

**Version**: 1.0  
**Last Updated**: 2024

