# How Employees Get Updates - Simple Explanation

## How It Works

1. **You push updates** → Files go to `G:\Company\Software\Updates`
2. **Employee starts their bot** → Bot automatically checks G-Drive for updates
3. **If update found** → Popup appears: "Update available! Update now?"
4. **Employee clicks "Yes"** → Bot downloads and installs update automatically
5. **Employee's data stays safe** → Passwords, settings preserved

---

## What You Need to Do

Add a small piece of code to each bot so it checks for updates when it starts.

**Don't worry - I'll show you exactly what to add!**

---

## Step-by-Step: Adding Update Code to a Bot

### Step 1: Find the Bot's Main File

Each bot has a main Python file (usually ends in `_bot.py` or `bot.py`)

### Step 2: Add This Code Near the Top (After Other Imports)

```python
# Add update checking
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Updates"))
    from update_manager import UpdateManager
    import tkinter.messagebox as msgbox
    UPDATE_CHECK_AVAILABLE = True
except:
    UPDATE_CHECK_AVAILABLE = False
```

### Step 3: Add This Function (Before Your Main Class)

```python
def check_for_updates():
    """Check for updates when bot starts"""
    if not UPDATE_CHECK_AVAILABLE:
        return False
    
    try:
        # Path to G-Drive updates folder
        update_source = r"G:\Company\Software\Updates"
        
        # Current bot directory
        bot_directory = Path(__file__).parent
        
        # Get bot name (you'll need to set this for each bot)
        bot_name = "YOUR_BOT_NAME_HERE"  # Change this!
        current_version = "1.0.0"  # Change this to match version.json!
        
        # Initialize update manager
        manager = UpdateManager(
            bot_name=bot_name,
            current_version=current_version,
            update_source=update_source,
            bot_directory=bot_directory,
            user_data_files=["*.json", "*.log"]  # Preserve user data
        )
        
        # Check for updates
        update_info = manager.check_for_updates()
        
        if update_info:
            # Show update dialog
            response = msgbox.askyesno(
                "Update Available",
                f"Version {update_info['new_version']} is available!\n\n"
                f"Current: {update_info['current_version']}\n\n"
                f"Would you like to update now?\n\n"
                f"(Your settings will be preserved)"
            )
            
            if response:
                # Install update
                result = manager.update(auto_install=True)
                if result['updated']:
                    msgbox.showinfo("Update Complete", "Please restart the bot.")
                    return True
        
        return False
    except Exception as e:
        # Don't crash if update check fails
        print(f"Update check failed: {e}")
        return False
```

### Step 4: Call It When Bot Starts

In your bot's `__init__` or `main()` function, add:

```python
# Check for updates (after window is created)
try:
    if check_for_updates():
        # Update was installed, close bot
        self.root.quit()  # or sys.exit() depending on your bot
except:
    pass  # Don't crash if update check fails
```

---

## That's It!

Once you add this code to each bot, employees will automatically get prompted to update when new versions are available.

---

## Need Help?

I can add this code to your bots for you! Just tell me which bot you want me to update first.

