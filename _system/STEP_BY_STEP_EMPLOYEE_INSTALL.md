# Step-by-Step: What Happens When Employee Installs

## 🎯 Employee's Experience

### Step 1: Employee Downloads Software

**What employee does:**
1. Receives `In-Office Installation` folder
2. Copies folder to their computer
3. Places it anywhere (Desktop, Documents, etc.)

**What happens:**
- Folder is ready for installation
- All files are present

---

### Step 2: Employee Runs `install_bots.bat`

**What employee does:**
1. Navigates to `_system` folder
2. Double-clicks `install_bots.bat`

**What happens:**
- Installation window opens
- Installation process begins

---

### Step 3: User Registration (Automatic)

**What employee sees:**
```
======================================================================
STEP 1: User Registration
======================================================================

To centralize data collection and track usage, please register:
(This information is stored securely and HIPAA-compliant)

Enter your name: [Employee types name]
```

**What happens:**
- Employee enters name (e.g., "John Smith")
- System registers employee automatically
- Computer ID generated: `abc123def456`
- Computer name detected: `DESKTOP-ABC123`
- **Data stored in:** `_user_directory/user_directory.db`
- **This file syncs to OneDrive** - you'll see it!

**Result:**
```
✓ Registration complete!
  Name: John Smith
  Computer: DESKTOP-ABC123
  Computer ID: abc123def456

✓ Data will be centralized in OneDrive for AI training.
```

---

### Step 4: Install Dependencies (Automatic)

**What employee sees:**
```
======================================================================
STEP 2: Installing Dependencies
======================================================================

Installing all dependencies for the enterprise AI system...
[Progress messages]
✓ All dependencies installed successfully!
```

**What happens:**
- All Python packages installed automatically
- Dependencies verified
- **No manual action needed**

---

### Step 5: Create Desktop Shortcut (Automatic)

**What employee sees:**
```
======================================================================
STEP 3: Creating Desktop Shortcut
======================================================================

Creating desktop shortcut...
✓ Desktop shortcut created successfully!
  Location: C:\Users\JohnSmith\Desktop
  Name: Automation Hub.lnk

✓ You can now launch Automation Hub from your desktop!
```

**What happens:**
- Desktop shortcut created automatically
- Shortcut appears on desktop: "Automation Hub.lnk"
- **Works on all Windows systems**

---

### Step 6: Installation Complete

**What employee sees:**
```
======================================================================
✓ Installation Complete!
======================================================================

Your data will be automatically centralized in OneDrive.
This allows the AI to learn from all employee usage patterns.

✓ Desktop shortcut created: Automation Hub.lnk
  You can launch Automation Hub from your desktop!

Press ENTER to close...
```

**What happens:**
- Installation complete
- Desktop shortcut ready
- Employee can start using Automation Hub

---

## 📊 What You See (Admin/You)

### Immediately After Employee Installs:

**On Your Computer (OneDrive):**

1. **User Registry Database:**
   - Location: `_user_directory/user_directory.db`
   - **Contains:** All registered employees
   - **Syncs automatically** via OneDrive (usually 1-2 minutes)

2. **Employee Data:**
   - Location: `_secure_data/` (from employee's computer)
   - Location: `_ai_intelligence/` (from employee's computer)
   - **Syncs automatically** via OneDrive

---

### How to See Registered Employees:

**Method 1: View User Registry (Easiest)**

**Run:**
```
_system\view_user_registry.bat
```

**What you'll see:**
```
[USERS] TOTAL REGISTERED USERS: 2

[LIST] Registered Users:

  1. John Smith
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

---

**Method 2: Check OneDrive Database**

**Location:**
```
In-Office Installation\_user_directory\user_directory.db
```

**Use SQLite browser:**
- Open `user_directory.db`
- View `registered_users` table
- See all registered employees

---

## 🧪 How to Test

### Test 1: Simulate Employee Installation

**On your computer:**

1. **Run test:**
   ```
   _system\test_employee_installation.bat
   ```

2. **When prompted:**
   - Enter test name: "Test Employee"

3. **After installation:**
   - Run `view_user_registry.bat`
   - See "Test Employee" in registry

---

### Test 2: View Registry

**Run:**
```
_system\view_user_registry.bat
```

**Verify:**
- All registered employees appear
- Computer information correct
- Registration dates recorded

---

### Test 3: Check OneDrive Sync

**Check:**
```
In-Office Installation\_user_directory\user_directory.db
```

**Verify:**
- File exists
- Contains registered employees
- Data synced via OneDrive

---

## 📁 File Locations

### On Employee's Computer:

**Created during installation:**
1. `_user_directory/user_directory.db` - User registry (syncs to OneDrive)
2. `_system/local_user.json` - Local user config (syncs to OneDrive)
3. Desktop shortcut: "Automation Hub.lnk"

**Created when using:**
4. `_secure_data/secure_collection.db` - Data collection (syncs to OneDrive)
5. `_ai_intelligence/workflow_database.db` - Intelligence data (syncs to OneDrive)

---

### On Your Computer (OneDrive):

**After employee installs (1-2 minutes):**
1. `_user_directory/user_directory.db` - All registered employees
2. `_secure_data/` folders - Data from all computers
3. `_ai_intelligence/` folders - Intelligence from all computers
4. `_centralized_data/centralized_data.db` - Aggregated data

---

## ✅ Complete Timeline

### T+0 seconds (Employee Installs):
- Employee runs `install_bots.bat`
- Employee enters name
- Registration stored locally
- Desktop shortcut created

### T+1-2 minutes (OneDrive Sync):
- OneDrive syncs `user_directory.db` to cloud
- File becomes available on your computer
- **You can see employee in registry!**

### T+24 hours (Data Aggregation):
- Data aggregated from employee's computer
- Appears in `_centralized_data/centralized_data.db`
- You can see employee's data statistics

---

## 🎯 Summary

### What Happens:

1. **Employee runs:** `install_bots.bat`
2. **Employee enters:** Name when prompted
3. **System creates:** User registration in database
4. **OneDrive syncs:** File to your computer (1-2 minutes)
5. **You view:** Run `view_user_registry.bat` to see all employees

### How to Test:

1. **Simulate employee:** Run `test_employee_installation.bat`
2. **View registry:** Run `view_user_registry.bat`
3. **Check OneDrive:** Verify `user_directory.db` synced

### How to See Employees:

**Easiest method:**
```
_system\view_user_registry.bat
```

**This shows:**
- ✅ All registered employees
- ✅ Which computer each employee is on
- ✅ Registration dates
- ✅ Data statistics

**You'll see all registered employees in the registry!** 🚀

