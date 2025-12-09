# Testing Guide - User Registration & Data Centralization

## 🎯 How to Test the System

### Step 1: Test Your Installation

**Run the test script:**

1. **Double-click:** `_system/test_user_registration.bat`
   - OR run: `python _system/test_user_registration.py`

2. **What it tests:**
   - ✅ OneDrive location verification
   - ✅ User registration system
   - ✅ Data centralization system
   - ✅ Directory structure
   - ✅ Database creation

**Expected output:**
- Shows installation directory location
- Shows if OneDrive sync is working
- Shows registered users (if any)
- Shows registered computers (if any)
- Shows data statistics

---

### Step 2: View User Registry

**View all registered users:**

1. **Double-click:** `_system/view_user_registry.bat`
   - OR run: `python _system/view_user_registry.py`

2. **What it shows:**
   - ✅ All registered users
   - ✅ Which computer each user is on
   - ✅ Registration dates
   - ✅ Last active times
   - ✅ Centralized data statistics

**Expected output:**
- List of all registered users
- Computer information for each user
- Total registered users count
- Total registered computers count
- Aggregated data statistics

---

### Step 3: Test with Other Users

**Have other employees register:**

1. **Have employee run:** `install_bots.bat`
2. **Employee enters:** Their name when prompted
3. **System registers:** Employee automatically
4. **You view:** Run `view_user_registry.bat` to see them

**What happens:**
- Employee name is registered
- Computer ID is generated
- Computer name is detected
- Data stored in `_user_directory/user_directory.db`
- **This file syncs via OneDrive** - you'll see it on your computer

---

## 📍 Your Installation Location

**Your installation is at:**
```
C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation
```

**✅ This is PERFECT for data centralization!**

**Why:**
- ✅ It's in OneDrive (cloud storage)
- ✅ OneDrive automatically syncs to all computers
- ✅ All data will be in one central location
- ✅ You'll see all users' data automatically

---

## 📊 How Data Centralization Works

### Step 1: Employee Registers

**What happens:**
1. Employee runs `install_bots.bat`
2. Employee enters their name
3. System registers them in `_user_directory/user_directory.db`
4. **This file syncs to OneDrive** - you'll see it!

**Where you can see it:**
- File: `_user_directory/user_directory.db`
- View with: `view_user_registry.bat`
- Location: Same OneDrive folder (you'll see it!)

---

### Step 2: Employee Uses Bots

**What happens:**
1. Employee uses bots
2. Data collected locally:
   - `_secure_data/secure_collection.db`
   - `_ai_intelligence/workflow_database.db`
3. **These files sync to OneDrive** - you'll see them!

**Where you can see it:**
- Files: `_secure_data/`, `_ai_intelligence/`
- Location: Same OneDrive folder (you'll see them!)

---

### Step 3: Data Aggregation

**What happens:**
1. System aggregates data daily
2. Combines data from all computers
3. Stores in: `_centralized_data/centralized_data.db`
4. **This file syncs to OneDrive** - you'll see it!

**Where you can see it:**
- File: `_centralized_data/centralized_data.db`
- View with: `view_user_registry.bat`
- Location: Same OneDrive folder (you'll see it!)

---

## ✅ What You'll See

### After Other Users Register

**You'll see in OneDrive:**
- ✅ `_user_directory/user_directory.db` - All registered users
- ✅ `_secure_data/` folders from all computers
- ✅ `_ai_intelligence/` folders from all computers
- ✅ `_centralized_data/centralized_data.db` - Aggregated data

**You'll see in Registry Viewer:**
- ✅ All registered user names
- ✅ Which computer each user is on
- ✅ Registration dates
- ✅ Data statistics per user
- ✅ Total aggregated data

---

## 🔍 How to Verify It Works

### Test 1: Register Yourself

1. **Run:** `install_bots.bat`
2. **Enter:** Your name when prompted
3. **Check:** Run `view_user_registry.bat`
4. **Verify:** You appear in the registry

**Expected result:**
- You see yourself in the registry
- Your computer is registered
- Data collection starts

---

### Test 2: Have Another User Register

1. **Have employee run:** `install_bots.bat` on their computer
2. **Employee enters:** Their name
3. **Wait:** OneDrive syncs (usually immediate)
4. **Check:** Run `view_user_registry.bat` on your computer
5. **Verify:** They appear in the registry

**Expected result:**
- New user appears in registry
- Their computer is registered
- Data from their computer becomes available

---

### Test 3: View Aggregated Data

1. **Have users use bots** (collect some data)
2. **Wait:** Data aggregation runs (daily)
3. **Check:** Run `view_user_registry.bat`
4. **Verify:** See aggregated data statistics

**Expected result:**
- See total bot executions
- See total AI prompts
- See total workflow patterns
- See data from all users

---

## 📁 File Locations You Can Check

### In Your OneDrive Folder:

```
In-Office Installation/
├── _user_directory/
│   └── user_directory.db          ← All registered users (you'll see this!)
│
├── _secure_data/                  ← Data from all computers (you'll see these!)
│   └── secure_collection.db
│
├── _ai_intelligence/               ← Data from all computers (you'll see these!)
│   └── workflow_database.db
│
└── _centralized_data/              ← Aggregated data (you'll see this!)
    └── centralized_data.db
```

**All these files sync via OneDrive - you'll see them on your computer!**

---

## 🎯 Quick Test Checklist

### ✅ Test Now:

1. **Run test script:**
   - `test_user_registration.bat`
   - Verify system is working

2. **View registry:**
   - `view_user_registry.bat`
   - See current users

3. **Register yourself (if not done):**
   - `install_bots.bat`
   - Enter your name

### ✅ Test with Other Users:

1. **Have employee register:**
   - Employee runs `install_bots.bat`
   - Employee enters name

2. **Wait for OneDrive sync:**
   - Usually immediate (1-2 minutes)
   - Files appear in OneDrive

3. **View registry:**
   - Run `view_user_registry.bat`
   - See new user in registry

4. **Verify data:**
   - Have user use bots
   - Wait for aggregation (daily)
   - View aggregated data

---

## 💡 Tips

### OneDrive Sync:

- **Automatic:** OneDrive syncs automatically
- **Timing:** Usually immediate (1-2 minutes)
- **Manual Sync:** Right-click OneDrive icon → Sync now

### Viewing Data:

- **Easy way:** Use `view_user_registry.bat`
- **Database:** Use SQLite browser to view `.db` files
- **Files:** All JSON files are human-readable

### Troubleshooting:

- **No users showing:** Wait for OneDrive sync
- **Data not appearing:** Check OneDrive sync status
- **Database errors:** Run `test_user_registration.bat` to diagnose

---

## ✅ Summary

### Your Setup:

**Location:** ✅ OneDrive (perfect for centralization!)

**You'll See:**
- ✅ All registered users in registry
- ✅ Data from all computers
- ✅ Aggregated data statistics
- ✅ Everything in OneDrive folder

### How to Test:

1. **Test now:** Run `test_user_registration.bat`
2. **View users:** Run `view_user_registry.bat`
3. **Have users register:** They run `install_bots.bat`
4. **See them:** Run `view_user_registry.bat` again

**Your OneDrive setup is perfect - you'll see all users' data automatically!** 🚀

