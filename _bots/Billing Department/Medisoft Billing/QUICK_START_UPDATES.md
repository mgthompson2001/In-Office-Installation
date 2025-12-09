# Quick Start: Auto-Update System

## 🚀 Get Started in 3 Steps

### Step 1: Initial Setup (Run Once - 5 minutes)

Run the setup script to create version files and manifests for all your bots:

```bash
python setup_update_system.py
```

This will:
- ✅ Create `version.json` for each bot
- ✅ Create `update_manifest.json` for each bot
- ✅ Set up the update system structure

**Location:** Run this in your master copy (OneDrive location).

---

### Step 2: Add Update Checker to Your Bots (15 minutes per bot)

Add this code to each bot's startup:

**For Medisoft Billing Bot** (`medisoft_billing_bot.py`):

1. **Add import at the top:**
```python
from update_manager import UpdateManager
from pathlib import Path
import tkinter.messagebox as msgbox
```

2. **Add this function before your main class:**
```python
def check_for_updates_on_startup():
    """Check for updates when bot starts."""
    try:
        # Detect OneDrive path
        onedrive_path = Path(os.environ.get('OneDrive', ''))
        if onedrive_path.exists():
            update_source = onedrive_path / "_bots" / "Billing Department" / "Medisoft Billing"
        else:
            # Fallback to local path
            update_source = Path(__file__).parent
        
        bot_directory = Path(__file__).parent
        
        manager = UpdateManager(
            bot_name="Medisoft Billing Bot",
            current_version="1.0.0",
            update_source=str(update_source),
            bot_directory=bot_directory,
            user_data_files=[
                "medisoft_users.json",
                "medisoft_coordinates.json"
            ]
        )
        
        update_info = manager.check_for_updates()
        
        if update_info:
            response = msgbox.askyesno(
                "Update Available",
                f"Version {update_info['new_version']} is available!\n\n"
                f"Would you like to update now?\n\n"
                f"(Your settings will be preserved)"
            )
            
            if response:
                result = manager.update(auto_install=True)
                if result['updated']:
                    msgbox.showinfo("Update Complete", "Please restart the bot.")
                    return True
        
        return False
    except Exception as e:
        logger.warning(f"Update check failed: {e}")
        return False
```

3. **Call it in your bot's `__init__` method:**
```python
# At the end of __init__
try:
    if check_for_updates_on_startup():
        self.root.after(2000, self.root.quit)  # Close after 2 seconds
except:
    pass
```

---

### Step 3: Release Updates (When You Make Changes)

When you want to push an update:

1. **Make your changes** to the bot files
2. **Run the release script:**
```bash
python release_update.py 1.0.1 "Fixed login bug, added new feature"
```

This will:
- ✅ Update `version.json` to the new version
- ✅ Regenerate `update_manifest.json` with current files
- ✅ Make the update available to all users

3. **Wait for OneDrive to sync** (usually instant)
4. **Done!** Users will be prompted to update on next startup

---

## 📋 That's It!

Your update system is now set up. Here's what happens:

1. **You make changes** → Run `release_update.py` → Update is available
2. **User starts bot** → Bot checks for updates → User is prompted
3. **User clicks "Yes"** → Update downloads and installs → User data is preserved
4. **User restarts bot** → New version is running!

---

## 🎯 Common Tasks

### Update a Single Bot

```bash
python release_update.py 1.0.1 "Fixed bug"
```

### Check Current Versions

Look in each bot's `version.json` file.

### Test Update System

1. Make a small change (e.g., change a label)
2. Run `release_update.py` with new version
3. Start the bot on a test computer
4. Verify update is detected and installed

---

## ❓ Troubleshooting

**Updates not detected?**
- Check OneDrive sync status
- Verify `version.json` exists in master copy
- Check update source path in bot code

**User data lost?**
- Check `_updates/backup_*` folders
- Restore from backup manually if needed

**Update fails?**
- Check bot has write permissions
- Ensure bot is closed before updating
- Check logs in `_updates/` directory

---

## 📚 More Information

- **Full setup guide:** `UPDATE_SYSTEM_SETUP_GUIDE.md`
- **All solutions:** `UPDATE_MANAGEMENT_SOLUTIONS.md`
- **Update manager code:** `update_manager.py`

---

## 🆘 Need Help?

1. Check the logs in `_updates/` directory
2. Review error messages in bot console
3. Test on one computer first before deploying

---

**You're all set!** 🎉

