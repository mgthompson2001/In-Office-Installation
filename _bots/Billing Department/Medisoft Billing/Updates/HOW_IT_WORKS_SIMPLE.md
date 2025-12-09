# How the Update System Works - Super Simple

## 🎯 The New Way (Much Simpler!)

Instead of modifying each bot, we have **ONE central update bot** that employees run.

---

## 📋 How It Works

### For You (Pushing Updates):

1. **Make changes** to your bots
2. **Run `PUSH_UPDATE.bat`**
3. **Done!** Files go to G-Drive

### For Employees (Getting Updates):

1. **Go to G-Drive:** `G:\Company\Software\Updates`
2. **Double-click:** `update_bot.bat`
3. **Select folder:** Browse to their In-Office Installation folder
4. **Click:** "Update All Bots"
5. **Done!** All bots updated

---

## 🎨 Timestamp Feature

Every bot's header shows when it was updated:
- **Title bar:** "Medisoft Billing Bot - Updated, 11/26/2025"
- **Header label:** "Medisoft Billing Bot - Updated, 11/26/2025"

This happens automatically when you push updates!

---

## ✅ Benefits

✅ **No code changes** - Don't need to modify each bot  
✅ **One place** - Employees run one program to update everything  
✅ **Visual confirmation** - Timestamp shows when updated  
✅ **Simple** - Much easier than the old way  

---

## 📁 What Gets Copied to G-Drive

When you run `PUSH_UPDATE.bat`, these files go to `G:\Company\Software\Updates\`:

- `update_bot.py` - The update manager (employees run this)
- `update_bot.bat` - Launcher
- `update_manager.py` - Core engine
- `Medisoft_Billing_Bot/` - Update files
- `Missed_Appointments_Tracker_Bot/` - Update files
- ... (all other bots)

---

## 🚀 That's It!

Much simpler than modifying each bot. Employees just run one program to update everything!

