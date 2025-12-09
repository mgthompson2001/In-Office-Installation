# Employee Installation Location Guide

## ⚠️ CRITICAL: Where to Install Software

### ✅ CORRECT: Install in OneDrive

**Employees MUST install the software in their OneDrive folder for data synchronization to work.**

---

## 📍 Where Employees Should Install

### Step 1: Copy Folder to OneDrive

**Employees should:**
1. Copy the entire `In-Office Installation` folder
2. Place it in their **OneDrive folder**
3. Location should be: `OneDrive\In-Office Installation\`

**Example paths:**
- `C:\Users\EmployeeName\OneDrive\In-Office Installation\`
- `C:\Users\EmployeeName\OneDrive - Integrity Senior Services\In-Office Installation\`
- `C:\Users\EmployeeName\OneDrive\Desktop\In-Office Installation\`

**Important:** The folder must be inside OneDrive (any subfolder is fine)

---

### Step 2: Run Installation

**After copying to OneDrive:**
1. Navigate to: `In-Office Installation\_system\`
2. Double-click: `install_bots.bat`
3. Enter employee name when prompted
4. Wait for installation to complete

---

### Step 3: Verify OneDrive Sync

**After installation:**
1. Check OneDrive icon in system tray
2. Verify it's syncing (no errors)
3. Wait 1-2 minutes for sync to complete

---

## ❌ WRONG: Don't Install Here

### These locations will NOT sync automatically:

- ❌ `C:\Users\EmployeeName\Desktop\` (if Desktop is not in OneDrive)
- ❌ `C:\Users\EmployeeName\Documents\` (if Documents is not in OneDrive)
- ❌ `C:\Program Files\`
- ❌ `C:\Program Files (x86)\`
- ❌ Any location outside OneDrive

**Note:** If Desktop/Documents are synced to OneDrive, those locations will work.

---

## ✅ How Data Syncs

### How It Works:

1. **Employee installs software in OneDrive:**
   - Location: `OneDrive\In-Office Installation\`

2. **Registration database created:**
   - Location: `OneDrive\In-Office Installation\_user_directory\user_directory.db`

3. **OneDrive syncs automatically:**
   - File syncs to cloud (1-2 minutes)
   - File appears on admin's computer via OneDrive

4. **Admin sees registration:**
   - Run `admin_dashboard.bat` or `view_user_registry.bat`
   - Employee appears in registry

---

## 📊 What Gets Synced

### Files That Sync via OneDrive:

1. **User Registry:**
   - `_user_directory\user_directory.db` - All registered employees

2. **Collected Data:**
   - `_secure_data\secure_collection.db` - Encrypted data
   - `_ai_intelligence\workflow_database.db` - Workflow patterns

3. **Centralized Data:**
   - `_centralized_data\centralized_data.db` - Aggregated data

4. **Local User Config:**
   - `_system\local_user.json` - Employee's local registration

---

## 🎯 Instructions for Employees

### Simple Instructions:

**Give employees these instructions:**

```
1. Copy the "In-Office Installation" folder to your OneDrive folder
   (Make sure it's inside OneDrive, not just on your Desktop)

2. Navigate to: In-Office Installation\_system\

3. Double-click: install_bots.bat

4. Enter your name when prompted

5. Wait for installation to complete

6. That's it! You're now registered and your data will sync automatically.
```

---

## ✅ Verification Checklist

### For Employees:

- [ ] Software folder is in OneDrive
- [ ] OneDrive is syncing (check system tray icon)
- [ ] Ran `install_bots.bat`
- [ ] Entered name during installation
- [ ] Installation completed successfully
- [ ] Desktop shortcut created

### For Admin:

- [ ] Wait 1-2 minutes for OneDrive sync
- [ ] Run `admin_dashboard.bat`
- [ ] Check if employee appears in registry
- [ ] Verify employee's computer information

---

## 🔍 How to Check OneDrive Sync

### For Employees:

**Check OneDrive sync status:**
1. Click OneDrive icon in system tray
2. Click "Settings"
3. Check "Account" tab
4. Verify "Status" shows "Up to date"

**Check if folder is in OneDrive:**
1. Open File Explorer
2. Navigate to OneDrive folder
3. Verify `In-Office Installation` folder exists
4. Check if it has OneDrive sync icon (cloud icon)

---

## 📁 Folder Structure (After Installation)

### In OneDrive:

```
OneDrive/
└── In-Office Installation/
    ├── _system/
    │   ├── install_bots.bat
    │   ├── local_user.json  ← Employee's local registration
    │   └── [other system files]
    │
    ├── _user_directory/
    │   └── user_directory.db  ← All registered employees (SYNCS!)
    │
    ├── _secure_data/
    │   └── secure_collection.db  ← Encrypted data (SYNCS!)
    │
    ├── _ai_intelligence/
    │   └── workflow_database.db  ← Workflow patterns (SYNCS!)
    │
    └── _centralized_data/
        └── centralized_data.db  ← Aggregated data (SYNCS!)
```

---

## 🚨 Troubleshooting

### Employee Not Appearing in Registry?

**Check:**

1. **Is folder in OneDrive?**
   - Verify `In-Office Installation` is inside OneDrive folder
   - Not just on Desktop (unless Desktop is in OneDrive)

2. **Is OneDrive syncing?**
   - Check OneDrive icon in system tray
   - Verify no sync errors
   - Right-click OneDrive icon → "Sync now"

3. **Did employee run install?**
   - Verify they ran `install_bots.bat`
   - Check if they entered their name
   - Check if installation completed

4. **Wait for sync:**
   - OneDrive sync can take 1-2 minutes
   - Wait and check again
   - Manually sync: Right-click OneDrive icon → "Sync now"

---

## 📊 Summary

### Critical Requirement:

**✅ Employees MUST install software in OneDrive folder**

**Why:**
- Registration database is stored in `_user_directory\user_directory.db`
- This file must be in OneDrive to sync to admin's computer
- If installed outside OneDrive, data won't sync automatically

### Installation Location:

**Correct:**
- `OneDrive\In-Office Installation\` ✅
- `OneDrive\Desktop\In-Office Installation\` ✅
- `OneDrive\Documents\In-Office Installation\` ✅

**Wrong:**
- `C:\Users\EmployeeName\Desktop\In-Office Installation\` (if Desktop not in OneDrive) ❌
- `C:\Program Files\In-Office Installation\` ❌
- Any location outside OneDrive ❌

### Timeline:

- **Immediately:** Employee registered locally
- **1-2 minutes:** OneDrive syncs to cloud
- **Admin sees:** Employee appears in registry

**Employees must install in OneDrive for data to sync!** 🚀

