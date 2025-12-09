# How to See Registered Employees

## 🎯 Quick Answer

**Run:** `view_user_registry.bat`

**This will show:**
- ✅ All registered employees
- ✅ Which computer each employee is on
- ✅ Registration dates
- ✅ Data statistics

---

## 📊 What Happens When Employee Installs

### Step-by-Step Process:

1. **Employee runs:** `install_bots.bat`
2. **Employee enters:** Their name when prompted
3. **System creates:** User registration in `_user_directory/user_directory.db`
4. **OneDrive syncs:** File appears on your computer (usually 1-2 minutes)
5. **You view:** Run `view_user_registry.bat` to see all employees

---

## 🔍 How to See Registered Employees

### Method 1: View User Registry (Easiest)

**Run:**
```
_system\view_user_registry.bat
```

**What you'll see:**
```
[USERS] TOTAL REGISTERED USERS: 3

[LIST] Registered Users:

  1. Employee Name 1
     Computer: DESKTOP-ABC123
     Computer ID: abc123def456
     Registered: 2025-11-05T12:00:00
     Last Active: 2025-11-05T12:00:00

  2. Employee Name 2
     Computer: DESKTOP-XYZ789
     Computer ID: xyz789ghi012
     Registered: 2025-11-05T11:00:00
     Last Active: 2025-11-05T12:30:00
```

---

### Method 2: Check OneDrive Database

**Location:**
```
In-Office Installation\_user_directory\user_directory.db
```

**How to view:**
1. **Use SQLite browser:**
   - Download: https://sqlitebrowser.org/
   - Open `user_directory.db`
   - View `registered_users` table

2. **OR use Python:**
   ```python
   import sqlite3
   conn = sqlite3.connect('_user_directory/user_directory.db')
   cursor = conn.cursor()
   cursor.execute("SELECT * FROM registered_users")
   for row in cursor.fetchall():
       print(row)
   ```

---

### Method 3: Check Local User Files

**Location:**
```
In-Office Installation\_system\local_user.json
```

**Note:** This shows the local user (you). To see all users, use Method 1 or 2.

---

## 📁 Where Employee Data Appears

### In OneDrive Folder:

**After employee installs, you'll see:**

1. **User Registry Database:**
   - `_user_directory/user_directory.db`
   - **Contains:** All registered employees
   - **Syncs automatically** via OneDrive

2. **Employee Data:**
   - `_secure_data/secure_collection.db` (from employee's computer)
   - `_ai_intelligence/workflow_database.db` (from employee's computer)
   - **Syncs automatically** via OneDrive

3. **Centralized Data:**
   - `_centralized_data/centralized_data.db`
   - **Contains:** Aggregated data from all employees
   - **Syncs automatically** via OneDrive

---

## ⏱️ Timeline

### When Employee Installs:

**Immediately (0-30 seconds):**
- Employee registered locally
- Data stored in `_user_directory/user_directory.db` on employee's computer

**Within 1-2 minutes:**
- OneDrive syncs file to cloud
- File becomes available on your computer
- You can see employee in registry

**Within 24 hours:**
- Data aggregated from employee's computer
- Appears in `_centralized_data/centralized_data.db`
- You can see employee's data statistics

---

## ✅ Verification Steps

### Step 1: Employee Installs

**Have employee:**
1. Copy `In-Office Installation` folder to their computer
2. Navigate to `_system` folder
3. Double-click `install_bots.bat`
4. Enter their name when prompted
5. Wait for installation to complete

---

### Step 2: Check OneDrive Sync

**On your computer:**
1. Navigate to: `In-Office Installation\_user_directory\`
2. Check if `user_directory.db` exists
3. If not, wait 1-2 minutes for OneDrive sync
4. OR right-click OneDrive icon → Sync now

---

### Step 3: View Registry

**On your computer:**
1. Run: `view_user_registry.bat`
2. Check for new employee in list
3. Verify their information

---

## 🧪 Test It Yourself

### Simulate Employee Installation:

**On your computer:**

1. **Run test:**
   ```
   _system\test_employee_installation.bat
   ```

2. **Enter test name:**
   - When prompted, enter: "Test Employee"

3. **Verify:**
   - Check desktop for "Automation Hub.lnk"
   - Run `view_user_registry.bat`
   - See "Test Employee" in registry

---

## 📊 What You'll See

### After Employee Registers:

**In User Registry:**
- ✅ Employee name
- ✅ Computer name
- ✅ Computer ID
- ✅ Registration date
- ✅ Last active time

**In OneDrive:**
- ✅ `user_directory.db` file
- ✅ Employee data folders
- ✅ Centralized data database

---

## ✅ Summary

### How to See Employees:

1. **Easiest:** Run `view_user_registry.bat`
2. **Database:** Check `_user_directory/user_directory.db`
3. **OneDrive:** Wait for sync, then check files

### Timeline:

- **Immediately:** Employee registered locally
- **1-2 minutes:** OneDrive syncs to your computer
- **You can see:** Run `view_user_registry.bat` anytime

**You'll see all registered employees in the registry!** 🚀

