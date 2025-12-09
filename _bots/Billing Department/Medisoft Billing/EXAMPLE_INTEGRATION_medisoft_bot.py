"""
EXAMPLE: How to integrate the update manager into medisoft_billing_bot.py

This file shows exactly what code to add to your existing bot.
Copy and paste these sections into your medisoft_billing_bot.py file.
"""

# ============================================================================
# STEP 1: Add this import near the top of medisoft_billing_bot.py
# ============================================================================
# Add this after the other imports (around line 20)

try:
    from update_manager import UpdateManager
    UPDATE_MANAGER_AVAILABLE = True
except ImportError:
    UPDATE_MANAGER_AVAILABLE = False
    UpdateManager = None


# ============================================================================
# STEP 2: Add this function before the MedisoftBillingBot class
# ============================================================================
# Add this around line 158, before "class MedisoftBillingBot:"

def check_for_updates_on_startup():
    """
    Check for updates when bot starts.
    Returns True if update was installed and bot should restart.
    """
    if not UPDATE_MANAGER_AVAILABLE:
        logger.debug("Update manager not available, skipping update check")
        return False
    
    try:
        # Detect OneDrive path automatically
        onedrive_path = Path(os.environ.get('OneDrive', ''))
        if not onedrive_path.exists():
            # Try alternative OneDrive path
            onedrive_path = Path(os.environ.get('OneDriveCommercial', ''))
        
        if onedrive_path.exists():
            # Path to your master copy in OneDrive
            update_source = onedrive_path / "_bots" / "Billing Department" / "Medisoft Billing"
        else:
            # Fallback: assume bot is in OneDrive already
            update_source = Path(__file__).parent
        
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
                # Add any PNG files that are saved selectors
            ]
        )
        
        # Check for updates
        update_info = manager.check_for_updates()
        
        if update_info:
            # Show update dialog
            response = messagebox.askyesno(
                "Update Available",
                f"A new version ({update_info['new_version']}) is available!\n\n"
                f"Current version: {update_info['current_version']}\n\n"
                f"Release notes:\n{update_info.get('release_notes', 'No release notes')}\n\n"
                f"Would you like to update now?\n\n"
                f"(Your settings and credentials will be preserved)",
                icon='question'
            )
            
            if response:
                # Download and install update
                result = manager.update(ask_permission=False, auto_install=True)
                
                if result['updated']:
                    messagebox.showinfo(
                        "Update Complete",
                        f"Successfully updated to version {result['new_version']}!\n\n"
                        f"Please restart the bot to use the new version.",
                        icon='info'
                    )
                    return True  # Signal to restart
                else:
                    messagebox.showerror(
                        "Update Failed",
                        f"Update failed: {result.get('error', 'Unknown error')}\n\n"
                        f"The bot will continue with the current version.",
                        icon='error'
                    )
        
        return False
        
    except Exception as e:
        # Don't block bot startup if update check fails
        logger.warning(f"Update check failed: {e}")
        return False


# ============================================================================
# STEP 3: Add this to the MedisoftBillingBot.__init__ method
# ============================================================================
# Add this at the END of the __init__ method (after line 201, before create_main_window is called)

# In your existing __init__ method, add this at the very end:
"""
        # Check for updates on startup (non-blocking)
        # This will be called after the window is created
        self.needs_restart = False
"""


# ============================================================================
# STEP 4: Add this to the create_main_window method
# ============================================================================
# Add this at the END of create_main_window method, after the window is fully created
# (around line 1100, after all widgets are created)

# Add this at the end of create_main_window, before the method returns:
"""
        # Check for updates after window is created
        # Use after() to check after window is displayed
        def check_updates():
            try:
                if check_for_updates_on_startup():
                    # Update was installed, close bot after 2 seconds
                    self.root.after(2000, self.root.quit)
            except Exception as e:
                logger.warning(f"Update check error: {e}")
        
        # Check for updates 1 second after window is shown
        self.root.after(1000, check_updates)
"""


# ============================================================================
# COMPLETE EXAMPLE: What the end of create_main_window should look like
# ============================================================================
"""
        # ... all your existing window creation code ...
        
        # Check for updates after window is created
        def check_updates():
            try:
                if check_for_updates_on_startup():
                    # Update was installed, close bot after 2 seconds
                    self.root.after(2000, self.root.quit)
            except Exception as e:
                logger.warning(f"Update check error: {e}")
        
        # Check for updates 1 second after window is shown
        self.root.after(1000, check_updates)
"""


# ============================================================================
# ALTERNATIVE: Simpler integration (check before window creation)
# ============================================================================
# If you prefer to check for updates BEFORE creating the window:

# In your main() function or at the end of the file, before creating the bot:
"""
def main():
    # Check for updates first
    if UPDATE_MANAGER_AVAILABLE:
        try:
            if check_for_updates_on_startup():
                # Update was installed, exit so user can restart
                print("Update installed. Please restart the bot.")
                return
        except Exception as e:
            logger.warning(f"Update check failed: {e}")
    
    # Create and run bot
    bot = MedisoftBillingBot()
    bot.run()
"""


# ============================================================================
# NOTES
# ============================================================================
"""
1. Update the current_version in check_for_updates_on_startup() when you release new versions
2. The update source path will automatically detect OneDrive
3. User data files (medisoft_users.json, medisoft_coordinates.json) are automatically preserved
4. If update check fails, the bot will still start normally
5. Users will be prompted to update when a new version is available
"""

