# Super Simple Instructions

## 🎯 What You Have Now

- **Your master folder:** `C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation`
- **Employees' update folder:** `G:\Company\Software\Updates`
- **Update control center:** `Updates/` folder

---

## 🚀 How to Push Updates (3 Steps)

### Step 1: Make Your Changes
Edit bot files in your master folder (In-Office Installation)

### Step 2: Update Version Number
```bash
python Updates/release_update.py 1.0.1 "Fixed bug, added feature"
```

### Step 3: Push to G-Drive
```bash
python Updates/sync_to_gdrive.py
```

**Done!** Employees will see updates on next bot startup.

---

## 📋 One-Time Setup (Do This Once)

### 1. Set Up Version Tracking
```bash
python Updates/setup_all_bots.py
```

This creates `version.json` files for each bot.

### 2. Test It
```bash
python Updates/sync_to_gdrive.py
```

Check that files appear in `G:\Company\Software\Updates\`

---

## ✅ That's It!

- **You work in:** Your master folder
- **You push with:** `python Updates/sync_to_gdrive.py`
- **Employees get from:** `G:\Company\Software\Updates\`
- **Employees update:** Automatically when they start their bots

---

## 🆘 Troubleshooting

**G-Drive path not working?**
- Check that `G:\Company\Software` exists
- Make sure you have write access
- Verify the path in `Updates/config.json`

**Files not syncing?**
- Make sure you're in the master folder when running scripts
- Check that bot source paths in `config.json` are correct

