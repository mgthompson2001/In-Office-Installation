# Admin Dashboard Guide

## 🎯 Quick Start

**Run:** `admin_dashboard.bat`

**This will show you:**
- ✅ All registered employees
- ✅ Employee statistics
- ✅ Detailed employee data (bot executions, AI prompts, workflow patterns)
- ✅ Aggregated data summary

---

## 📊 What You Can View

### 1. Employee Registry

**Shows:**
- All registered employees
- Which computer each employee is on
- Registration dates
- Last active times

---

### 2. Employee Data (Detailed)

**For each employee, you can view:**
- **Bot Executions:**
  - Which bots they ran
  - When they ran them
  - Parameters used
  - Results

- **AI Prompts:**
  - Prompts they entered into AI Task Assistant
  - Responses received
  - Which bots were executed
  - Timestamps

- **Workflow Patterns:**
  - Common workflow patterns
  - Frequency of use
  - Last used dates

---

### 3. Aggregated Data Summary

**Shows:**
- Total bot executions (all employees)
- Total AI prompts (all employees)
- Total workflow patterns (all employees)
- Unique users count
- Unique computers count
- Total records

---

## 🔍 How to Use

### Method 1: View All Employees (Quick)

**Run:**
```
_system\admin_dashboard.bat
```

**What you'll see:**
- List of all registered employees
- Summary statistics
- Option to view detailed data for specific employee

---

### Method 2: View Specific Employee Data

**Run:**
```
_system\admin_dashboard.bat
```

**Then:**
1. View list of all employees
2. When prompted, enter 'y' to view specific employee data
3. Enter employee name
4. View detailed data for that employee

---

### Method 3: View Registry Only (Quick)

**Run:**
```
_system\view_user_registry.bat
```

**What you'll see:**
- All registered employees
- Computer information
- Basic statistics

---

## 📁 Where Data is Stored

### Database Locations:

1. **User Registry:**
   - Location: `_user_directory/user_directory.db`
   - Contains: All registered employees

2. **Centralized Data:**
   - Location: `_centralized_data/centralized_data.db`
   - Contains: All collected data (bot executions, AI prompts, workflow patterns)

3. **Secure Data:**
   - Location: `_secure_data/secure_collection.db`
   - Contains: HIPAA-compliant encrypted data

4. **AI Intelligence:**
   - Location: `_ai_intelligence/workflow_database.db`
   - Contains: Workflow patterns and insights

---

## 🧪 Example Output

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

## ✅ Features

### What You Can Do:

1. **View All Employees:**
   - See all registered employees at once
   - View their computer information
   - See registration dates

2. **View Employee Data:**
   - See detailed data for any employee
   - View bot executions
   - View AI prompts
   - View workflow patterns

3. **View Summary Statistics:**
   - See aggregated data across all employees
   - View total records
   - See unique users and computers

4. **Export Data (Coming Soon):**
   - Export employee data to CSV
   - Export reports to PDF
   - Generate analytics reports

---

## 📊 Data Collection Timeline

### When Data Appears:

**Immediately:**
- Employee registration (when they run `install_bots.bat`)

**After 1-2 minutes:**
- OneDrive syncs data to your computer
- You can see employee in registry

**After 24 hours:**
- Data aggregated from all computers
- Appears in `_centralized_data/centralized_data.db`
- You can see detailed statistics

---

## 🔍 Troubleshooting

### No Employees Showing?

**Check:**
1. Have employees run `install_bots.bat`?
2. Did they enter their name during installation?
3. Is OneDrive syncing? (Check OneDrive sync status)

**Solution:**
- Wait 1-2 minutes for OneDrive sync
- Right-click OneDrive icon → Sync now
- Re-run `admin_dashboard.bat`

---

### No Data for Employee?

**Check:**
1. Has employee used any bots?
2. Has employee used AI Task Assistant?
3. Is data collection enabled?

**Solution:**
- Data appears after employees start using bots
- Check `_centralized_data/centralized_data.db` exists
- Wait 24 hours for data aggregation

---

### Database Not Found?

**Check:**
1. Does `_centralized_data/` folder exist?
2. Does `centralized_data.db` exist?
3. Is OneDrive syncing?

**Solution:**
- Data will be created automatically when employees use bots
- Ensure OneDrive is syncing
- Check folder permissions

---

## 🎯 Summary

### How to View Employees:

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

- **User Registry:** `_user_directory/user_directory.db`
- **Centralized Data:** `_centralized_data/centralized_data.db`
- **Secure Data:** `_secure_data/secure_collection.db`

### Timeline:

- **Immediately:** Employee registration visible
- **1-2 minutes:** OneDrive syncs to your computer
- **24 hours:** Data aggregated and available

**You'll see all employees and their data in the dashboard!** 🚀

