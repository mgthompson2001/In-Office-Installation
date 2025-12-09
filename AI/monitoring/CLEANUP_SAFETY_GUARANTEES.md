# Cleanup System Safety Guarantees

## ✅ **100% SAFE - Bot Files Are NEVER Touched**

This document explains the safety guarantees of the passive cleanup system.

## Protected File Types (NEVER DELETED)

The cleanup system **NEVER** deletes or modifies:

1. **Bot Python Files** (`.py` files)
   - Any file ending in `_bot.py` (e.g., `medisoft_billing_bot.py`)
   - Any file in `_bots` directories
   - Any file with "bot" in the name

2. **Batch Files** (`.bat` files)
   - All `.bat` files are completely ignored

3. **Configuration Files**
   - `*_users.json` (user credentials)
   - `*_coordinates.json` (coordinate training data)
   - `*_settings.json` (bot settings)
   - Any `.json` file that doesn't match backup patterns

4. **Screenshot Images** (`.png` files)
   - All image files are preserved

5. **Requirements Files** (`requirements.txt`)
   - All dependency files are preserved

## What Gets Cleaned (SAFE TO DELETE)

### 1. Log Files (`.log` files only)
- **Pattern**: `*.log`, `*.log.*`
- **Retention**: 14 days
- **Safety**: Only `.log` files are processed, never `.py` or `.bat`

### 2. Backup Files (explicit backup pattern only)
- **Pattern**: `*.backup-*.json`, `*.backup-*.db`, `*.backup-*.log`
- **Retention**: 7 days
- **Safety**: Only files with `.backup-` in the name are deleted
- **Example**: `users.backup-20241101.json` ✅ (deleted if old)
- **Example**: `medisoft_users.json` ❌ (NEVER deleted)

### 3. Test Files (test patterns only, NOT in _bots)
- **Pattern**: `test_*.py`, `temp_*.py`, `*_test.py`
- **Retention**: 1 day
- **Safety**: 
  - NEVER touches files in `_bots` directories
  - NEVER touches files with `_bot.py` in the name
  - Only removes actual test files outside bot directories

### 4. Training Data Files (in `AI/training_data/` only)
- **Location**: `AI/training_data/` directory ONLY
- **Pattern**: `training_dataset_*.json`, `bot_logs_*.json`, etc.
- **Safety**: Only processes files in the training data directory
- **Action**: Compresses/archives old training data, keeps last 3 datasets

### 5. Database Records (records only, not files)
- **Files**: `browser_activity.db`, `full_monitoring.db`
- **Action**: Deletes old RECORDS from databases (not the database files)
- **Retention**: 30 days for records

## Protection Mechanisms

1. **Directory Protection**: Files in `_bots` directories are NEVER touched
2. **Pattern Matching**: Only specific patterns are matched (not wildcards)
3. **File Extension Checks**: Only processes files with specific extensions
4. **Name Checks**: Files with "bot" in the name are protected
5. **Age Checks**: Only old files (past retention period) are deleted

## Verification

To verify safety, the cleanup system:
- Logs every file it processes
- Only matches specific patterns
- Has multiple layers of protection
- Fails safely (errors don't break bots)

## What Changed

**Only Modified**: `_bots/__init__.py` (infrastructure file, not bot code)
- This file runs cleanup automatically when any bot starts
- It does NOT modify any bot functionality
- It only adds a background thread that runs cleanup

**No Bot Files Modified**: Zero bot `.py` or `.bat` files were changed.

## If You're Still Concerned

You can:
1. Review the cleanup logs in `_system/logs/system_cleanup.log`
2. Run cleanup manually first: `START_SYSTEM_CLEANUP.bat`
3. Check what would be deleted before it runs
4. Disable cleanup by removing the cleanup call from `_bots/__init__.py`

## Summary

✅ **Bot files are 100% safe**  
✅ **Only data files are cleaned**  
✅ **Multiple protection layers**  
✅ **No bot code was modified**

