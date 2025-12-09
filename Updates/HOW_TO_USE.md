# How to Use the Update System - Super Simple Guide

## 🎯 What This Does

Instead of manually updating each computer, you:
1. Make changes to your bots
2. Run 2 scripts
3. **Done!** Everyone gets the update automatically

---

## 📋 First Time Setup (Do This Once - 5 minutes)

### Step 1: Set Up Version Tracking
Double-click or run this in Command Prompt:
```
python Updates\setup_all_bots.py
```

This creates version files for all your bots. You only need to do this once.

### Step 2: Test It
Double-click or run:
```
python Updates\sync_to_gdrive.py
```

This copies your bots to G-Drive. Check that files appear in `G:\Company\Software\Updates\`

**That's it for setup!**

---

## 🚀 How to Roll Out Updates (Every Time You Make Changes)

### Step 1: Make Your Changes
Edit your bot files in your master folder (In-Office Installation)

### Step 2: Update the Version Number
Double-click or run:
```
python Updates\release_update.py 1.0.1 "Fixed login bug"
```

Replace `1.0.1` with your new version number (like 1.0.2, 1.1.0, etc.)
Replace `"Fixed login bug"` with what you changed

### Step 3: Push to G-Drive
Double-click or run:
```
python Updates\sync_to_gdrive.py
```

**Done!** Updates are now on G-Drive. Employees will see them when they start their bots.

---

## 📁 Where Everything Goes

**Your Master Folder:**
- `C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation`
- This is where you edit your bots

**G-Drive (Where Employees Get Updates):**
- `G:\Company\Software\Updates`
- Your scripts automatically copy files here

**Employees' Computers:**
- Bots are installed locally on each computer
- When they start a bot, it checks `G:\Company\Software\Updates` for updates
- If an update is found, they get a popup asking if they want to update

---

## ✅ What Happens When You Update

1. **You make changes** → Edit bot files
2. **You run scripts** → `release_update.py` then `sync_to_gdrive.py`
3. **Files go to G-Drive** → `G:\Company\Software\Updates`
4. **Employee starts bot** → Bot checks G-Drive
5. **Employee sees popup** → "Update available! Update now?"
6. **Employee clicks "Yes"** → Bot updates itself automatically
7. **Employee's data stays safe** → Credentials, settings preserved

---

## 🎯 Quick Reference

**To push an update:**
```
python Updates\release_update.py 1.0.1 "What you changed"
python Updates\sync_to_gdrive.py
```

**To check if G-Drive is accessible:**
- Open File Explorer
- Go to `G:\Company\Software`
- You should see an `Updates` folder

---

## 🆘 Troubleshooting

**Scripts don't run?**
- Make sure Python is installed
- Try opening Command Prompt, navigate to your master folder, then run the scripts

**G-Drive not found?**
- Check that `G:\Company\Software` exists
- Make sure you have access to G-Drive

**Employees not seeing updates?**
- Make sure you ran both scripts (`release_update.py` and `sync_to_gdrive.py`)
- Check that files are in `G:\Company\Software\Updates`
- Employees need to restart their bots to see updates

---

## 💡 Tips

- **Version numbers:** Use format like 1.0.1, 1.0.2, 1.1.0 (major.minor.patch)
- **Release notes:** Keep them short and clear (what you fixed/added)
- **Test first:** Test updates on one computer before pushing to everyone
- **Backup:** The system automatically backs up employee data before updating

---

## 📞 Need Help?

Check these files in the Updates folder:
- `SIMPLE_INSTRUCTIONS.md` - Even simpler guide
- `README_FINAL.md` - Complete overview
- `config.json` - Configuration (usually doesn't need changes)

---

**That's it! You're ready to roll out updates!** 🎉

