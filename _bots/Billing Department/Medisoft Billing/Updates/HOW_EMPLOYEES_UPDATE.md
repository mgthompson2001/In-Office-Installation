# How Employees Update Their Software

## Simple Explanation

When you push updates to G-Drive, employees' bots will automatically check for updates when they start. Here's how it works:

---

## The Process

1. **You push an update** → Run `PUSH_UPDATE.bat` → Files go to `G:\Company\Software\Updates`

2. **Employee starts their bot** → Bot automatically checks `G:\Company\Software\Updates` for updates

3. **If update found** → Popup appears:
   ```
   Update Available!
   
   Version 1.0.1 is available!
   Current version: 1.0.0
   
   Release notes: Fixed login bug
   
   Would you like to update now?
   (Your settings and credentials will be preserved)
   
   [Yes] [No]
   ```

4. **Employee clicks "Yes"** → Bot automatically:
   - Downloads update files
   - Backs up their data (passwords, settings)
   - Installs new files
   - Restores their data
   - Shows "Update complete! Please restart the bot."

5. **Employee restarts bot** → New version is running!

---

## What You Need to Do

**Add update checking code to each bot** so they check G-Drive when they start.

### Option 1: I Can Do It For You (Easiest)

Tell me which bot you want me to update first, and I'll add the code for you!

### Option 2: You Do It Yourself

See `ADD_TO_BOTS.md` for step-by-step instructions.

---

## Important Notes

- **Employees don't need to do anything special** - updates happen automatically
- **Their data stays safe** - passwords, settings, saved files are preserved
- **They can say "No"** - if they don't want to update right now, bot still works
- **Update check is optional** - if it fails, bot still starts normally

---

## What Happens If Employee Says "No"?

- Bot continues with current version
- They'll be asked again next time they start the bot
- They can update later by restarting the bot

---

## Testing

To test the update system:

1. Push an update using `PUSH_UPDATE.bat`
2. Start a bot on a test computer
3. You should see the update popup
4. Click "Yes" to test the update process

---

## Need Help?

- See `ADD_TO_BOTS.md` for code examples
- See `update_checker_simple.py` for copy-paste code
- Or ask me to add it to your bots!

