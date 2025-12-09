# Auto-Update System Setup Guide

## Quick Start (30 minutes)

This guide will help you set up automatic updates for all your bots using the OneDrive/SharePoint sync method.

---

## Step 1: Prepare Your Master Copy (5 minutes)

### 1.1 Create Version File

In your master copy (OneDrive location), create a `version.json` file in each bot directory:

**For Medisoft Billing Bot:**
```json
{
  "version": "1.0.0",
  "bot_name": "Medisoft Billing Bot",
  "release_date": "2024-01-15T10:00:00",
  "release_notes": "Initial release with auto-update support"
}
```

### 1.2 Create Update Manifest

Run this Python script in each bot directory to create the manifest:

```python
from pathlib import Path
from update_manager import create_update_manifest

# For Medisoft Billing Bot
create_update_manifest(
    bot_directory=Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\_bots\Billing Department\Medisoft Billing"),
    exclude_patterns=[
        "*.log",
        "medisoft_users.json",  # User data - preserve this
        "medisoft_coordinates.json",  # User data - preserve this
        "__pycache__",
        "*.pyc",
        "_updates",
        "vendor",
        "*.png"  # Saved selector images - preserve these
    ]
)
```

This creates `update_manifest.json` listing all files to update.

---

## Step 2: Add Update Checker to Your Bots (15 minutes)

### 2.1 Add to Medisoft Billing Bot

Open `medisoft_billing_bot.py` and add this near the top (after imports):

```python
# Add update manager import
from update_manager import UpdateManager
from pathlib import Path
import tkinter.messagebox as msgbox

# Add this function before the main window class
def check_for_updates_on_startup():
    """Check for updates when bot starts."""
    try:
        # Path to your OneDrive master copy
        update_source = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\_bots\Billing Department\Medisoft Billing")
        
        # Current bot directory
        bot_directory = Path(__file__).parent
        
        # Initialize update manager
        manager = UpdateManager(
            bot_name="Medisoft Billing Bot",
            current_version="1.0.0",  # Update this when you release new versions
            update_source=str(update_source),
            bot_directory=bot_directory,
            user_data_files=[
                "medisoft_users.json",
                "medisoft_coordinates.json",
                "*.png"  # Saved selector images
            ]
        )
        
        # Check for updates
        update_info = manager.check_for_updates()
        
        if update_info:
            # Ask user if they want to update
            response = msgbox.askyesno(
                "Update Available",
                f"A new version ({update_info['new_version']}) is available!\n\n"
                f"Current version: {update_info['current_version']}\n\n"
                f"Release notes:\n{update_info.get('release_notes', 'No release notes')}\n\n"
                f"Would you like to update now?\n\n"
                f"(Your settings and credentials will be preserved)"
            )
            
            if response:
                # Download and install update
                result = manager.update(ask_permission=False, auto_install=True)
                
                if result['updated']:
                    msgbox.showinfo(
                        "Update Complete",
                        f"Successfully updated to version {result['new_version']}!\n\n"
                        f"Please restart the bot to use the new version."
                    )
                    return True  # Signal to restart
                else:
                    msgbox.showerror(
                        "Update Failed",
                        f"Update failed: {result.get('error', 'Unknown error')}\n\n"
                        f"The bot will continue with the current version."
                    )
        
        return False
        
    except Exception as e:
        # Don't block bot startup if update check fails
        logger.warning(f"Update check failed: {e}")
        return False
```

### 2.2 Call Update Checker on Startup

In your `MedisoftBillingBot` class `__init__` method, add this at the end:

```python
# Check for updates (non-blocking)
try:
    needs_restart = check_for_updates_on_startup()
    if needs_restart:
        # Optionally auto-restart
        self.root.after(2000, self.root.quit)  # Close after 2 seconds
except:
    pass  # Don't crash if update check fails
```

---

## Step 3: Configure Update Source Path (5 minutes)

### Option A: Use OneDrive Path (Recommended)

The update source path should point to your OneDrive master copy. Since each user's OneDrive path is different, you can:

1. **Use a relative path** if bots are installed in OneDrive
2. **Use environment variable** to detect OneDrive location
3. **Use a network path** if you have a shared drive

### Option B: Use Network Path

If you have a network drive:

```python
update_source = r"\\server\share\bots\Medisoft Billing"
```

### Option C: Use Environment Variable

```python
import os
onedrive_path = os.environ.get('OneDrive', '')
if onedrive_path:
    update_source = Path(onedrive_path) / "_bots" / "Billing Department" / "Medisoft Billing"
else:
    # Fallback to local path
    update_source = Path(__file__).parent
```

---

## Step 4: Test the Update System (5 minutes)

### 4.1 Create a Test Update

1. Make a small change to your bot (e.g., change a label text)
2. Update `version.json` to `1.0.1`
3. Run `create_update_manifest()` again to update the manifest
4. Wait for OneDrive to sync

### 4.2 Test on a User Computer

1. Start the bot
2. It should detect the update
3. Click "Yes" to update
4. Verify the change is applied
5. Verify user data (credentials) is preserved

---

## Step 5: Deploy to All Users

### 5.1 Update All Bots

Repeat Step 2 for each bot:
- Missed Appointments Tracker Bot
- Real Estate Financial Tracker
- Therapy Notes Records Bot

### 5.2 Create Version Files

Create `version.json` in each bot's master copy directory.

### 5.3 Create Update Manifests

Run `create_update_manifest()` for each bot.

---

## How to Release Updates

### When You Want to Push an Update:

1. **Make your changes** to the master copy in OneDrive
2. **Update version.json:**
   ```json
   {
     "version": "1.0.2",
     "bot_name": "Medisoft Billing Bot",
     "release_date": "2024-01-20T10:00:00",
     "release_notes": "Fixed login bug, added new feature"
   }
   ```
3. **Regenerate update manifest:**
   ```python
   from update_manager import create_update_manifest
   create_update_manifest(bot_directory=Path("..."))
   ```
4. **Wait for OneDrive to sync** (usually instant, but can take a few minutes)
5. **Done!** Users will be prompted to update the next time they start the bot

---

## Advanced Configuration

### Silent Updates (No User Prompt)

To automatically install updates without asking:

```python
result = manager.update(ask_permission=False, auto_install=True)
```

### Scheduled Update Checks

Check for updates periodically while bot is running:

```python
def check_updates_periodically():
    """Check for updates every hour."""
    update_info = manager.check_for_updates()
    if update_info:
        # Show notification
        pass
    # Schedule next check
    root.after(3600000, check_updates_periodically)  # 1 hour
```

### Force Updates

To require users to update before using the bot:

```python
update_info = manager.check_for_updates()
if update_info:
    result = manager.update(auto_install=True)
    if not result['updated']:
        msgbox.showerror("Update Required", "You must update to continue.")
        sys.exit(1)
```

---

## Troubleshooting

### Updates Not Detected

1. **Check OneDrive sync:** Make sure master copy is synced
2. **Check version.json:** Ensure it exists and has correct format
3. **Check paths:** Verify update_source path is correct
4. **Check logs:** Look for errors in bot log file

### User Data Lost After Update

1. **Check backup:** Look in `_updates/backup_*` folders
2. **Restore manually:** Copy files from backup folder
3. **Check user_data_files:** Ensure all user data files are listed

### Update Fails

1. **Check permissions:** Bot needs write access to bot directory
2. **Check disk space:** Ensure enough space for update
3. **Check file locks:** Close bot before updating
4. **Check logs:** Look for specific error messages

---

## Security Considerations

1. **Verify update source:** Only accept updates from trusted location
2. **Validate files:** Consider adding file hash verification
3. **Backup user data:** Always backup before updating
4. **Test updates:** Test updates on one computer before deploying

---

## Next Steps

1. ✅ Set up version files for all bots
2. ✅ Add update checker to all bots
3. ✅ Test update system
4. ✅ Deploy to users
5. ✅ Make your first update!

---

## Support

If you need help:
1. Check the logs in `_updates/` directory
2. Review error messages in bot console
3. Test update process on a single computer first

---

## Example: Complete Integration

Here's a complete example of integrating the update system:

```python
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from update_manager import UpdateManager
import logging

logger = logging.getLogger(__name__)

class MyBot:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_update_manager()
        self.check_for_updates()
        # ... rest of your bot code ...
    
    def setup_update_manager(self):
        """Initialize update manager."""
        onedrive_path = Path(os.environ.get('OneDrive', ''))
        if onedrive_path.exists():
            update_source = onedrive_path / "_bots" / "Billing Department" / "Medisoft Billing"
        else:
            update_source = Path(__file__).parent
        
        self.update_manager = UpdateManager(
            bot_name="Medisoft Billing Bot",
            current_version="1.0.0",
            update_source=str(update_source),
            bot_directory=Path(__file__).parent,
            user_data_files=[
                "medisoft_users.json",
                "medisoft_coordinates.json"
            ]
        )
    
    def check_for_updates(self):
        """Check for updates on startup."""
        try:
            update_info = self.update_manager.check_for_updates()
            if update_info:
                self.prompt_for_update(update_info)
        except Exception as e:
            logger.warning(f"Update check failed: {e}")
    
    def prompt_for_update(self, update_info):
        """Show update dialog."""
        response = messagebox.askyesno(
            "Update Available",
            f"Version {update_info['new_version']} is available!\n\n"
            f"Would you like to update now?"
        )
        if response:
            self.install_update(update_info)
    
    def install_update(self, update_info):
        """Install the update."""
        result = self.update_manager.update(auto_install=True)
        if result['updated']:
            messagebox.showinfo("Update Complete", "Please restart the bot.")
            self.root.quit()
        else:
            messagebox.showerror("Update Failed", result.get('error', 'Unknown error'))
```

---

That's it! Your bots will now automatically check for and install updates while preserving user data.

