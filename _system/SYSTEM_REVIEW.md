# System Review - Your Installation Location

## 📍 Your Installation Location

**Your installation is at:**
```
C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation
```

**✅ PERFECT for Data Centralization!**

**Why:**
- ✅ It's in OneDrive (cloud storage)
- ✅ OneDrive automatically syncs to all computers
- ✅ All data will be in one central location
- ✅ You'll see all users' data automatically

---

## ✅ What You'll See After Other Users Register

### 1. User Registry Database

**Location:** `_user_directory/user_directory.db`

**What you'll see:**
- ✅ All registered user names
- ✅ Which computer each user is on
- ✅ Registration dates
- ✅ Last active times

**How to view:**
- Run: `view_user_registry.bat`
- OR: Use SQLite browser to view the database

---

### 2. Centralized Data Database

**Location:** `_centralized_data/centralized_data.db`

**What you'll see:**
- ✅ Bot executions from all users
- ✅ AI prompts from all employees
- ✅ Workflow patterns from all users
- ✅ Aggregated data statistics

**How to view:**
- Run: `view_user_registry.bat`
- OR: Use SQLite browser to view the database

---

### 3. Data from All Computers

**Locations:**
- `_secure_data/` (from all computers - synced via OneDrive)
- `_ai_intelligence/` (from all computers - synced via OneDrive)
- `_admin_data/` (from all computers - synced via OneDrive)

**What you'll see:**
- ✅ Data folders from all employee computers
- ✅ Each computer's data synced to OneDrive
- ✅ All data in one location

---

## 🔍 How to Test

### Test 1: Verify Your Location

**Run:**
```
python _system/test_user_registration.py
```

**What it checks:**
- ✅ Installation directory exists
- ✅ OneDrive location verified
- ✅ User directory created
- ✅ Database created

---

### Test 2: View User Registry

**Run:**
```
python _system/view_user_registry.py
```

**What it shows:**
- ✅ All registered users
- ✅ Which computer each user is on
- ✅ Registration information
- ✅ Data statistics

---

### Test 3: Register Yourself

**Run:**
```
install_bots.bat
```

**What happens:**
- ✅ You enter your name
- ✅ System registers you
- ✅ You appear in registry

---

### Test 4: Have Another User Register

**Steps:**
1. Employee runs `install_bots.bat` on their computer
2. Employee enters their name
3. Wait for OneDrive sync (1-2 minutes)
4. Run `view_user_registry.bat` on your computer
5. See them in the registry!

---

## 📊 How Data Centralization Works

### Step 1: Employee Registers

**What happens:**
- Employee runs `install_bots.bat`
- Employee enters name
- Data stored in `_user_directory/user_directory.db`
- **This file syncs to OneDrive** - you'll see it!

**Where you'll see it:**
- File: `_user_directory/user_directory.db`
- View with: `view_user_registry.bat`
- Location: Same OneDrive folder (you'll see it!)

---

### Step 2: Employee Uses Bots

**What happens:**
- Employee uses bots
- Data collected locally
- Stored in `_secure_data/`, `_ai_intelligence/`
- **These folders sync to OneDrive** - you'll see them!

**Where you'll see it:**
- Folders: `_secure_data/`, `_ai_intelligence/`
- Location: Same OneDrive folder (you'll see them!)

---

### Step 3: Data Aggregation

**What happens:**
- System aggregates data daily
- Combines data from all computers
- Stores in `_centralized_data/centralized_data.db`
- **This file syncs to OneDrive** - you'll see it!

**Where you'll see it:**
- File: `_centralized_data/centralized_data.db`
- View with: `view_user_registry.bat`
- Location: Same OneDrive folder (you'll see it!)

---

## ✅ Summary

### Your Location is Perfect:

**Location:** ✅ OneDrive (cloud storage)

**You'll See:**
- ✅ All registered users in registry
- ✅ Data from all computers
- ✅ Aggregated data statistics
- ✅ Everything in OneDrive folder

### How to View:

1. **Test system:** Run `test_user_registration.bat`
2. **View users:** Run `view_user_registry.bat`
3. **Have users register:** They run `install_bots.bat`
4. **See them:** Run `view_user_registry.bat` again

**Your OneDrive setup is perfect - you'll see all users' data automatically!** 🚀

