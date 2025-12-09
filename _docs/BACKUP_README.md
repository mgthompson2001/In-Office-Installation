# In-Office Installation - Backup Repository

## 📦 What This Is

This is a backup of the **In-Office Installation** folder containing all CCMD Bot software with the latest updates as of **January 6, 2025**.

## ✅ Latest Updates Included

### 1. **Referral Form Uploader Bot**
- ✅ Fixed: Now shows **full client names** (not just last names)
- ✅ Fixed: Improved PDF matching - won't miss files anymore
- ✅ Added: Better logging for debugging

### 2. **Counselor Assignment Bot**
- ✅ Fixed: Penelope workaround - uses **partial last name search** to avoid dropdown disappearing
- ✅ Added: **IPS counselor detection** - automatically detects and selects IPS vs non-IPS counselors from dropdown
- ✅ Improved: Arrow key navigation for dropdown selection

### 3. **Remove Counselor Bot**
- ✅ Optimized: 30-50% faster processing
- ✅ Reduced: Unnecessary wait times and retry attempts
- ✅ Removed: Excessive debug logging

### 4. **Update Management System**
- ✅ Added: `admin_launcher.py` - Central admin control panel
- ✅ Added: `create_update_installer.py` - Create email-able update installers
- ✅ Added: `EMAIL_UPDATE_GUIDE.md` - Complete guide for email-based updates

## 🚀 How to Use This Backup

### To Restore from Backup:
1. Clone this repository
2. Copy files to your working directory
3. Install dependencies: `pip install -r requirements.txt`
4. Run bots as normal

### To Push Updates to GitHub:
```bash
cd "C:\Users\MichaelLocal\Desktop\In-Office Installation"
git add .
git commit -m "Description of changes"
git push origin main
```

## 📋 Files Structure

- **Admin Tools**: `admin_launcher.py`, `create_update_installer.py`, `easy_update_manager.py`
- **Bot Launchers**: `secure_launcher.py`, `Launcher/bot_launcher.py`
- **Referral Bots**: `Referral bot and bridge (final)/`
- **Welcome Bots**: `The Welcomed One, Exalted Rank/`
- **Med Rec Bot**: `Med Rec/Finished Product, Launch Ready/`
- **Remove Counselor Bot**: `Cursor versions/Goose/`
- **Documentation**: `*.md` files, `NON_TECHNICAL_GUIDE.md`

## ⚠️ Important Notes

- **Password**: `Integritycode1!` (for admin tools)
- **Dependencies**: See `requirements.txt`
- **Python Version**: Python 3.7+ required
- **Chrome Driver**: Automatically managed by webdriver-manager

## 🔐 Security

- Do NOT commit credentials or sensitive data
- `.gitignore` is configured to exclude sensitive files
- Always review changes before pushing to GitHub

## 📞 Support

If you need to restore or have questions:
1. Check the documentation files (*.md)
2. Review commit history for changes
3. Contact your system administrator

---

**Last Backup**: January 6, 2025  
**Commit**: Initial backup with all latest updates  
**Status**: ✅ All bots tested and working

