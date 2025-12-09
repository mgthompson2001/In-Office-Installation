# Where to Find Employees in Registry and Review Collected Data

## 🎯 Quick Answer

**Run:** `admin_dashboard.bat`

**Location:** `_system\admin_dashboard.bat`

**This will show you:**
- ✅ All registered employees
- ✅ Employee statistics
- ✅ Detailed employee data (bot executions, AI prompts, workflow patterns)
- ✅ Aggregated data summary

---

## 📊 Three Ways to View Employee Data

### Method 1: Admin Dashboard (Comprehensive - Recommended)

**Run:**
```
_system\admin_dashboard.bat
```

**What you'll see:**
1. **All Registered Employees:**
   - Name
   - Computer name
   - Computer ID
   - Registration date
   - Last active time

2. **Aggregated Data Summary:**
   - Total bot executions (all employees)
   - Total AI prompts (all employees)
   - Total workflow patterns (all employees)
   - Unique users count
   - Unique computers count

3. **Detailed Employee Data (Optional):**
   - Bot executions (which bots, when, parameters, results)
   - AI prompts (prompts entered, responses, bots used)
   - Workflow patterns (common patterns, frequency)

---

### Method 2: User Registry Viewer (Quick View)

**Run:**
```
_system\view_user_registry.bat
```

**What you'll see:**
- All registered employees
- Computer information
- Basic statistics
- Option to view specific user data

---

### Method 3: Direct Database Access (Advanced)

**Database Locations:**

1. **User Registry:**
   - Location: `_user_directory\user_directory.db`
   - Contains: All registered employees

2. **Centralized Data:**
   - Location: `_centralized_data\centralized_data.db`
   - Contains: All collected data (bot executions, AI prompts, workflow patterns)

3. **Secure Data:**
   - Location: `_secure_data\secure_collection.db`
   - Contains: HIPAA-compliant encrypted data

**How to view:**
- Use SQLite browser: https://sqlitebrowser.org/
- Open the database file
- View tables directly

---

## 📁 Where Data is Stored

### In OneDrive Folder:

```
In-Office Installation/
├── _user_directory/
│   └── user_directory.db  ← All registered employees here!
│
├── _centralized_data/
│   └── centralized_data.db  ← All collected data here!
│
├── _secure_data/
│   └── secure_collection.db  ← Encrypted data here!
│
└── _ai_intelligence/
    └── workflow_database.db  ← Workflow patterns here!
```

---

## 🔍 Step-by-Step: How to Review Employee Data

### Step 1: Open Admin Dashboard

**Run:**
```
_system\admin_dashboard.bat
```

---

### Step 2: View All Employees

**You'll see:**
- List of all registered employees
- Their computer information
- Registration dates

---

### Step 3: View Summary Statistics

**You'll see:**
- Total bot executions (all employees)
- Total AI prompts (all employees)
- Total workflow patterns (all employees)
- Unique users and computers

---

### Step 4: View Specific Employee Data (Optional)

**When prompted:**
1. Enter 'y' to view specific employee data
2. Enter employee name
3. View detailed data:
   - Bot executions (which bots, when, parameters, results)
   - AI prompts (prompts entered, responses, bots used)
   - Workflow patterns (common patterns, frequency)

---

## 📊 What Data You Can See

### For Each Employee:

1. **Bot Executions:**
   - Which bots they ran
   - When they ran them
   - Parameters used (what files, what inputs)
   - Results (success/failure)

2. **AI Prompts:**
   - Prompts they entered into AI Task Assistant
   - Responses received
   - Which bots were executed
   - Timestamps

3. **Workflow Patterns:**
   - Common workflow patterns
   - Frequency of use
   - Last used dates

---

## 🧪 Example: What You'll See

### Employee List:

```
======================================================================
REGISTERED EMPLOYEES
======================================================================

[USERS] TOTAL REGISTERED EMPLOYEES: 3

1. John Smith
   Computer: DESKTOP-ABC123
   Computer ID: abc123def456
   Registered: 2025-11-05T12:00:00
   Last Active: 2025-11-05T14:30:00

2. Jane Doe
   Computer: DESKTOP-XYZ789
   Computer ID: xyz789ghi012
   Registered: 2025-11-05T11:00:00
   Last Active: 2025-11-05T15:00:00

3. Michael Thompson
   Computer: ISS-JKPZS34
   Computer ID: 2b29333397b43800
   Registered: 2025-11-05T14:34:10
   Last Active: 2025-11-05T14:34:10
```

### Employee Details:

```
======================================================================
EMPLOYEE INFORMATION
======================================================================
Name: John Smith
Computer: DESKTOP-ABC123
Computer ID: abc123def456
Registered: 2025-11-05T12:00:00
Last Active: 2025-11-05T14:30:00

======================================================================
DATA STATISTICS
======================================================================
Bot Executions: 15
AI Prompts: 8
Workflow Patterns: 3
Total Records: 26

======================================================================
RECENT BOT EXECUTIONS (10 shown)
======================================================================

1. Bot: claims_bot.py
   Time: 2025-11-05T14:30:00
   Parameters: {"client": "ABC Corp", "date_range": "2025-01-01 to 2025-11-05"}
   Result: Success

2. Bot: report_generator.py
   Time: 2025-11-05T14:25:00
   Parameters: {"report_type": "weekly", "output_format": "pdf"}
   Result: Success
```

---

## ⏱️ Timeline: When Data Appears

### Immediately:
- Employee registration (when they run `install_bots.bat`)

### After 1-2 minutes:
- OneDrive syncs data to your computer
- You can see employee in registry

### After 24 hours:
- Data aggregated from all computers
- Appears in `_centralized_data/centralized_data.db`
- You can see detailed statistics

---

## ✅ Summary

### How to Find Employees:

**Easiest method:**
```
_system\admin_dashboard.bat
```

**What you'll see:**
- ✅ All registered employees
- ✅ Employee statistics
- ✅ Detailed employee data
- ✅ Aggregated data summary

### Database Locations:

- **User Registry:** `_user_directory\user_directory.db`
- **Centralized Data:** `_centralized_data\centralized_data.db`
- **Secure Data:** `_secure_data\secure_collection.db`

### Quick Access:

1. **Admin Dashboard:** `_system\admin_dashboard.bat` (Comprehensive)
2. **User Registry:** `_system\view_user_registry.bat` (Quick view)
3. **Database Files:** Direct access via SQLite browser

**You'll see all employees and their data in the dashboard!** 🚀

