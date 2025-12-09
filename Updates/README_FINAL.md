# Update System - Complete Setup

## ✅ Configuration Complete!

Your update system is now configured with:

- **Your master folder:** `C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation`
- **Employees' update location:** `G:\Company\Software\Updates`
- **All 4 bots configured:** Medisoft, Missed Appointments, Real Estate, Therapy Notes

---

## 🚀 Quick Start (3 Steps to Push Updates)

### Step 1: Make Your Changes
Edit bot files in your master folder

### Step 2: Update Version
```bash
python Updates/release_update.py 1.0.1 "Fixed bug, added feature"
```

### Step 3: Push to G-Drive
```bash
python Updates/sync_to_gdrive.py
```

**Done!** Updates are now in `G:\Company\Software\Updates\`

---

## 📋 One-Time Setup (Do This Once)

### 1. Set Up Version Tracking
```bash
python Updates/setup_all_bots.py
```

This creates `version.json` and `update_manifest.json` for each bot in your master folder.

### 2. Test the Sync
```bash
python Updates/sync_to_gdrive.py
```

Check that files appear in `G:\Company\Software\Updates\`

---

## 📁 How It Works

```
Your Master Folder (In-Office Installation)
├── _bots/
│   └── Billing Department/
│       └── Medisoft Billing/
│           ├── medisoft_billing_bot.py
│           ├── version.json          ← Created by setup
│           ├── update_manifest.json  ← Created by setup
│           ├── Missed Appointments Tracker Bot/
│           └── Real Estate Financial Tracker/
└── Updates/
    ├── config.json                   ← Configuration
    ├── sync_to_gdrive.py             ← Push updates
    └── release_update.py             ← Update versions

G-Drive (Employees Access)
└── Company/
    └── Software/
        └── Updates/                  ← Where employees get updates
            ├── Medisoft_Billing_Bot/
            ├── Missed_Appointments_Tracker_Bot/
            ├── Real_Estate_Financial_Tracker/
            └── Therapy_Notes_Records_Bot/
```

---

## 🔄 Update Flow

1. **You edit** bot files in master folder
2. **You run** `release_update.py` → Updates version numbers
3. **You run** `sync_to_gdrive.py` → Copies to `G:\Company\Software\Updates\`
4. **Employee starts bot** → Bot checks `G:\Company\Software\Updates\` for updates
5. **Employee clicks "Update"** → Bot downloads and installs update
6. **Employee's data preserved** → Credentials, settings stay safe

---

## 📝 Next Steps

1. **Run setup:** `python Updates/setup_all_bots.py`
2. **Test sync:** `python Updates/sync_to_gdrive.py`
3. **Add update code to bots** (see integration examples)
4. **Make your first update!**

---

## 🆘 Need Help?

- **Simple instructions:** See `SIMPLE_INSTRUCTIONS.md`
- **Detailed guide:** See `QUICK_START.md`
- **Config file:** `Updates/config.json`

---

## ✅ You're All Set!

The system is configured and ready to use. Just run the setup script and start pushing updates!

