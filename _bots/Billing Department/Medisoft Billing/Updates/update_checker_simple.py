"""
Simple update checker code to add to your bots.
Copy this code into each bot's main file.
"""

# ============================================================================
# STEP 1: Add these imports at the top of your bot file (after other imports)
# ============================================================================

try:
    import sys
    from pathlib import Path
    # Add Updates folder to path so we can import update_manager
    updates_path = Path(__file__).parent.parent.parent / "Updates"
    if not updates_path.exists():
        # Try alternative path (if bot is in different location)
        updates_path = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\Updates")
    
    if updates_path.exists():
        sys.path.insert(0, str(updates_path))
        from update_manager import UpdateManager
        import tkinter.messagebox as msgbox
        UPDATE_CHECK_AVAILABLE = True
    else:
        UPDATE_CHECK_AVAILABLE = False
except:
    UPDATE_CHECK_AVAILABLE = False


# ============================================================================
# STEP 2: Add this function before your main bot class
# ============================================================================

def check_for_updates_on_startup(bot_name, current_version, user_data_files=None):
    """
    Check for updates when bot starts.
    
    Args:
        bot_name: Name of your bot (e.g., "Medisoft Billing Bot")
        current_version: Current version (e.g., "1.0.0")
        user_data_files: List of files to preserve (e.g., ["*.json", "*.log"])
    
    Returns:
        True if update was installed (bot should restart), False otherwise
    """
    if not UPDATE_CHECK_AVAILABLE:
        return False
    
    try:
        # Path to G-Drive updates folder (where you push updates)
        update_source = r"G:\Company\Software\Updates"
        
        # Current bot directory (where bot is installed on employee's computer)
        bot_directory = Path(__file__).parent
        
        # Default user data files to preserve
        if user_data_files is None:
            user_data_files = ["*.json", "*.log"]
        
        # Initialize update manager
        manager = UpdateManager(
            bot_name=bot_name,
            current_version=current_version,
            update_source=update_source,
            bot_directory=bot_directory,
            user_data_files=user_data_files
        )
        
        # Check for updates
        update_info = manager.check_for_updates()
        
        if update_info:
            # Show update dialog
            response = msgbox.askyesno(
                "Update Available",
                f"Version {update_info['new_version']} is available!\n\n"
                f"Current version: {update_info['current_version']}\n\n"
                f"Release notes:\n{update_info.get('release_notes', 'No release notes')}\n\n"
                f"Would you like to update now?\n\n"
                f"(Your settings and credentials will be preserved)",
                icon='question'
            )
            
            if response:
                # Install update
                result = manager.update(auto_install=True)
                if result['updated']:
                    msgbox.showinfo(
                        "Update Complete",
                        f"Successfully updated to version {result['new_version']}!\n\n"
                        f"Please restart the bot to use the new version.",
                        icon='info'
                    )
                    return True  # Signal to restart
                else:
                    msgbox.showerror(
                        "Update Failed",
                        f"Update failed: {result.get('error', 'Unknown error')}\n\n"
                        f"The bot will continue with the current version.",
                        icon='error'
                    )
        
        return False
        
    except Exception as e:
        # Don't crash bot if update check fails
        print(f"Update check failed: {e}")
        import logging
        logging.getLogger(__name__).warning(f"Update check failed: {e}")
        return False


# ============================================================================
# STEP 3: Call this function when your bot starts
# ============================================================================

# Example 1: In your bot's __init__ method (after creating the window)
"""
def __init__(self):
    # ... your existing initialization code ...
    
    # Create window first
    self.root = tk.Tk()
    # ... create all widgets ...
    
    # Check for updates after window is created
    def check_updates():
        try:
            if check_for_updates_on_startup(
                bot_name="Medisoft Billing Bot",  # Change this!
                current_version="1.0.0",  # Change this!
                user_data_files=["medisoft_users.json", "medisoft_coordinates.json"]
            ):
                # Update was installed, close bot after 2 seconds
                self.root.after(2000, self.root.quit)
        except:
            pass
    
    # Check for updates 1 second after window is shown
    self.root.after(1000, check_updates)
"""

# Example 2: In your main() function (before creating bot)
"""
def main():
    # Check for updates first
    if check_for_updates_on_startup(
        bot_name="Medisoft Billing Bot",
        current_version="1.0.0",
        user_data_files=["medisoft_users.json", "medisoft_coordinates.json"]
    ):
        # Update was installed, exit so user can restart
        print("Update installed. Please restart the bot.")
        return
    
    # Create and run bot
    bot = MedisoftBillingBot()
    bot.run()
"""

# ============================================================================
# STEP 4: Copy update_manager.py to each bot's directory (optional)
# ============================================================================

# Option A: Keep update_manager.py in Updates folder (recommended)
# - Bots import from Updates folder (code above does this)

# Option B: Copy update_manager.py to each bot folder
# - Each bot has its own copy
# - Change import to: from update_manager import UpdateManager

