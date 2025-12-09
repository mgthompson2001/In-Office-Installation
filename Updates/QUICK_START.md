# Quick Start: G-Drive Update System

## 🎯 How It Works (Super Simple)

1. **You make changes** to bots in `Updates/bots/` folder
2. **Run `sync_to_gdrive.py`** → Updates go to company G-Drive
3. **Employees' bots check G-Drive** → They get prompted to update
4. **Done!** Everyone has the latest version

---

## 📋 Setup Steps (One Time)

### Step 1: Configure G-Drive Path (2 minutes)

1. Open `Updates/config.json`
2. Find the `"gdrive_path"` line
3. Set it to your G-Drive path, for example:
   - `"gdrive_path": "G:\\"` (if G: is mapped)
   - `"gdrive_path": "C:\\Users\\YourName\\Google Drive"` (if local)
4. Save the file

**OR** run the helper script:
```bash
python Updates/get_gdrive_helper.py
```

### Step 2: Verify Master Folder Path (1 minute)

The `config.json` already has your master folder path set. Verify it's correct:
- Should be: `C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation`

### Step 3: Set Up Version Tracking (2 minutes)

Run:
```bash
python setup_all_bots.py
```

This creates `version.json` and `update_manifest.json` for each bot.

### Step 4: Push to G-Drive (1 minute)

Run:
```bash
python sync_to_gdrive.py
```

This copies everything to G-Drive.

---

## 🚀 Releasing Updates (30 seconds)

When you want to push an update:

1. **Make your changes** to bot files in your master folder (In-Office Installation)
2. **Update version:**
   ```bash
   python Updates/release_update.py 1.0.1 "Fixed bug, added feature"
   ```
3. **Push to G-Drive:**
   ```bash
   python Updates/sync_to_gdrive.py
   ```
4. **Done!** Employees will see updates on next bot startup

---

## 📁 Folder Structure

```
In-Office Installation/           ← Your master folder (where you develop)
├── _bots/
│   └── Billing Department/
│       └── Medisoft Billing/
│           ├── medisoft_billing_bot.py
│           ├── Missed Appointments Tracker Bot/
│           └── Real Estate Financial Tracker/
├── Updates/                      ← Update control center
│   ├── config.json               ← Configuration
│   ├── setup_all_bots.py         ← One-time setup
│   ├── release_update.py         ← Release new versions
│   └── sync_to_gdrive.py         ← Push to G-Drive

G-Drive/
└── Company/
    └── Software/
        └── Updates/              ← Where employees get updates
            ├── Medisoft_Billing_Bot/
            ├── Missed_Appointments_Tracker_Bot/
            ├── Real_Estate_Financial_Tracker/
            └── Therapy_Notes_Records_Bot/
```

---

## ✅ That's It!

- **You work in:** Your master folder (`In-Office Installation/`)
- **You push with:** `Updates/sync_to_gdrive.py`
- **Employees get from:** G-Drive `Company\Software\Updates\` folder
- **Employees update:** Automatically when they start their bots

---

## 🆘 Troubleshooting

**G-Drive not found?**
- Edit `config.json` and set `gdrive_path` manually
- Make sure G-Drive is synced/accessible

**Bots not syncing?**
- Check that bot folders exist in `Updates/bots/`
- Make sure G-Drive path is correct in `config.json`

**Employees not seeing updates?**
- Make sure you ran `sync_to_gdrive.py` after making changes
- Check that G-Drive folder `Bot Updates/` exists
- Verify employees' bots are checking the correct G-Drive path

