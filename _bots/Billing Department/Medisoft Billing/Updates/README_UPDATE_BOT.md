# Centralized Update Bot - How It Works

## 🎯 The New System

Instead of modifying each bot's code, we have **one central update bot** that employees run to update all their software.

---

## 📋 How It Works

### For You (Pushing Updates):

1. **Make changes** to your bots
2. **Run `PUSH_UPDATE.bat`** → Files go to `G:\Company\Software\Updates\`
3. **Done!** Updates are available

### For Employees (Getting Updates):

1. **Open G-Drive** → Go to `G:\Company\Software\Updates\`
2. **Double-click `update_bot.bat`** → Update Manager opens
3. **Select installation folder** → Browse to their In-Office Installation folder
4. **Click "Update All Bots"** → All bots update automatically
5. **Done!** All bots are updated

---

## 🎨 Timestamp Feature

Every bot's header now shows when it was last updated:
- **Title bar:** "Medisoft Billing Bot - Updated, 11/26/2025"
- **Header label:** "Medisoft Billing Bot - Updated, 11/26/2025"

This happens automatically when you push updates!

---

## 📁 Files in G-Drive Updates Folder

```
G:\Company\Software\Updates\
├── update_bot.py          ← The update manager (employees run this)
├── update_bot.bat         ← Launcher for update bot
├── update_manager.py      ← Core update engine
├── Medisoft_Billing_Bot/  ← Update files for each bot
├── Missed_Appointments_Tracker_Bot/
└── ... (other bots)
```

---

## ✅ Benefits

✅ **No code changes needed** - Bots don't need update checking code  
✅ **Centralized** - One place to update everything  
✅ **Simple for employees** - Just run one program  
✅ **Visual confirmation** - Timestamp shows when updated  
✅ **Safe** - User data is preserved automatically  

---

## 🚀 Next Steps

1. **Copy `update_bot.py` and `update_bot.bat` to G-Drive** when you push updates
2. **Tell employees** to run `update_bot.bat` from G-Drive to update
3. **That's it!** Much simpler than modifying each bot

---

## 📝 Employee Instructions

**To update your software:**

1. Open File Explorer
2. Go to: `G:\Company\Software\Updates`
3. Double-click: `update_bot.bat`
4. Click "Browse..." and select your In-Office Installation folder
5. Click "Update All Bots"
6. Wait for updates to complete
7. Done! All your bots are updated

---

This is much simpler and cleaner! 🎉

