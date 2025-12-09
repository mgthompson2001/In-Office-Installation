# Employee Installation Test Guide

## 🎯 What Happens When Employee Runs `install_bots.bat`

### Complete Installation Process:

**Step 1: Employee Downloads Software**
- Employee copies `In-Office Installation` folder to their computer
- Folder can be anywhere (Desktop, Documents, etc.)
- Should be in OneDrive folder for data centralization

**Step 2: Employee Runs `install_bots.bat`**
- Double-clicks `install_bots.bat` in `_system` folder
- Installation window opens

**Step 3: User Registration (Automatic)**
```
STEP 1: User Registration
==========================
Enter your name: [Employee enters name]
```
- Employee enters their name
- System registers them automatically
- Computer ID generated
- Computer name detected
- **Data stored in: `_user_directory/user_directory.db`**
- **This file syncs to OneDrive** - you'll see it!

**Step 4: Install Dependencies (Automatic)**
```
STEP 2: Installing Dependencies
=================================
Installing all dependencies...
```
- All Python packages installed automatically
- Dependencies verified
- **No manual action needed**

**Step 5: Create Desktop Shortcut (Automatic)**
```
STEP 3: Creating Desktop Shortcut
===================================
Creating desktop shortcut...
✓ Desktop shortcut created successfully!
  Location: [Desktop path]
  Name: Automation Hub.lnk
```
- Desktop shortcut created automatically
- Appears on desktop: "Automation Hub.lnk"
- **Works on all Windows systems**

**Step 6: Installation Complete**
```
✓ Installation Complete!
✓ Desktop shortcut created: Automation Hub.lnk
  You can launch Automation Hub from your desktop!
```

---

## 📊 What You'll See in OneDrive

### After Employee Installs:

**In Your OneDrive Folder:**

1. **User Registry Database:**
   - Location: `_user_directory/user_directory.db`
   - Contains: All registered employees
   - **You'll see this file sync to your computer!**

2. **User Data:**
   - Location: `_secure_data/` (from employee's computer)
   - Location: `_ai_intelligence/` (from employee's computer)
   - **These folders sync via OneDrive** - you'll see them!

3. **Centralized Data:**
   - Location: `_centralized_data/centralized_data.db`
   - Contains: Aggregated data from all employees
   - **You'll see this file sync to your computer!**

---

## 🔍 How to Test

### Test 1: Simulate Employee Installation

**On Your Computer:**

1. **Create test folder:**
   - Copy `In-Office Installation` to a test location
   - OR use a different folder name to simulate employee

2. **Run installation:**
   - Navigate to `_system` folder
   - Double-click `install_bots.bat`
   - Enter a test name (e.g., "Test Employee")

3. **Verify:**
   - Check desktop for "Automation Hub.lnk" shortcut
   - Check `_user_directory/user_directory.db` for new user
   - Run `view_user_registry.bat` to see registered users

---

### Test 2: View Registered Employees

**On Your Computer:**

1. **Run registry viewer:**
   ```
   _system\view_user_registry.bat
   ```

2. **What you'll see:**
   - All registered employees
   - Which computer each employee is on
   - Registration dates
   - Last active times
   - Data statistics

---

### Test 3: Verify OneDrive Sync

**On Your Computer:**

1. **Check OneDrive folder:**
   - Navigate to: `In-Office Installation\_user_directory\`
   - Open: `user_directory.db` (if synced)
   - OR wait for OneDrive to sync

2. **Verify:**
   - File should appear after employee registers
   - Usually syncs within 1-2 minutes
   - Can manually sync: Right-click OneDrive icon → Sync now

---

## 📁 Files Created During Installation

### On Employee's Computer:

1. **Desktop Shortcut:**
   - Location: Desktop
   - Name: "Automation Hub.lnk"
   - Points to: `_system\launch_automation_hub.vbs`

2. **User Registration:**
   - Location: `_user_directory/user_directory.db`
   - Contains: Employee name, computer ID, registration date
   - **Syncs to OneDrive** - you'll see it!

3. **Local User Config:**
   - Location: `_system/local_user.json`
   - Contains: Employee's local registration info
   - **Syncs to OneDrive** - you'll see it!

4. **Data Directories:**
   - `_secure_data/` - Data collection (syncs to OneDrive)
   - `_ai_intelligence/` - Intelligence data (syncs to OneDrive)
   - `_admin_data/` - Admin data (syncs to OneDrive)

---

## ✅ How to Verify Employee Registration

### Method 1: View User Registry (Easiest)

**Run:**
```
_system\view_user_registry.bat
```

**What you'll see:**
- All registered employees
- Which computer each employee is on
- Registration dates
- Data statistics

---

### Method 2: Check Database Directly

**Location:**
```
In-Office Installation\_user_directory\user_directory.db
```

**Use SQLite browser:**
- Open `user_directory.db`
- View `registered_users` table
- See all registered employees

---

### Method 3: Check OneDrive Files

**Check these files in OneDrive:**
1. `_user_directory/user_directory.db` - All registered users
2. `_secure_data/` folders - Data from all computers
3. `_ai_intelligence/` folders - Intelligence from all computers
4. `_centralized_data/centralized_data.db` - Aggregated data

**If files don't appear:**
- Wait 1-2 minutes for OneDrive sync
- Right-click OneDrive icon → Sync now
- Check OneDrive sync status

---

## 🧪 Complete Test Scenario

### Simulate Employee Installation:

**Step 1: Create Test Installation**
```
1. Copy "In-Office Installation" folder to test location
2. OR rename folder to simulate different employee
```

**Step 2: Run Installation**
```
1. Navigate to _system folder
2. Double-click install_bots.bat
3. Enter test name: "Test Employee"
4. Wait for installation to complete
```

**Step 3: Verify Registration**
```
1. Run: view_user_registry.bat
2. Check for "Test Employee" in registry
3. Verify computer information
```

**Step 4: Check OneDrive**
```
1. Navigate to OneDrive folder
2. Check _user_directory/user_directory.db
3. Verify employee appears in database
```

---

## 📊 What You'll See After Employee Registers

### In User Registry Viewer:

```
[USERS] TOTAL REGISTERED USERS: 2

[LIST] Registered Users:

  1. Test Employee
     Computer: DESKTOP-ABC123
     Computer ID: abc123def456
     Registered: 2025-11-05T12:00:00
     Last Active: 2025-11-05T12:00:00

  2. Your Name
     Computer: DESKTOP-XYZ789
     Computer ID: xyz789ghi012
     Registered: 2025-11-05T11:00:00
     Last Active: 2025-11-05T12:30:00
```

### In OneDrive Folder:

```
In-Office Installation/
├── _user_directory/
│   └── user_directory.db  ← All registered users here!
│
├── _secure_data/          ← Data from all computers
│   └── secure_collection.db
│
└── _centralized_data/     ← Aggregated data
    └── centralized_data.db
```

---

## ✅ Testing Checklist

### Test Installation Process:

- [ ] Employee runs `install_bots.bat`
- [ ] Employee enters name when prompted
- [ ] Dependencies install successfully
- [ ] Desktop shortcut created automatically
- [ ] Installation completes successfully

### Test Registration:

- [ ] Employee appears in user registry
- [ ] Computer information correct
- [ ] Registration date recorded
- [ ] User data stored in database

### Test OneDrive Sync:

- [ ] `user_directory.db` appears in OneDrive
- [ ] File syncs to your computer
- [ ] Can view registered users
- [ ] Data from employee's computer available

---

## 🎯 Summary

### What Happens:

1. **Employee runs:** `install_bots.bat`
2. **System automatically:**
   - Registers employee (Step 1)
   - Installs dependencies (Step 2)
   - Creates desktop shortcut (Step 3)
3. **Data stored in:** `_user_directory/user_directory.db`
4. **OneDrive syncs:** File appears on your computer
5. **You view:** Run `view_user_registry.bat` to see all employees

### How to Test:

1. **Simulate employee:** Run `install_bots.bat` with test name
2. **View registry:** Run `view_user_registry.bat`
3. **Check OneDrive:** Verify `user_directory.db` synced

**You'll see all registered employees in the registry!** 🚀

