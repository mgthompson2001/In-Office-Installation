#!/usr/bin/env python3
"""Quick verification script to check if data collection is working"""

from pathlib import Path
import sqlite3
from datetime import datetime, timedelta

# Installation directory
installation_dir = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")

print("=" * 70)
print("DATA COLLECTION VERIFICATION")
print("=" * 70)
print()

# Check secure collection database
secure_db = installation_dir / "_secure_data" / "secure_collection.db"
print(f"[1] Checking Secure Collection Database...")
print(f"    Location: {secure_db}")
print(f"    Exists: {secure_db.exists()}")
print()

if secure_db.exists():
    try:
        conn = sqlite3.connect(secure_db)
        cursor = conn.cursor()
        
        # Check bot executions in last 24 hours
        cursor.execute("""
            SELECT COUNT(*) FROM bot_executions 
            WHERE timestamp > datetime('now', '-1 day')
        """)
        count = cursor.fetchone()[0]
        print(f"    Bot executions in last 24 hours: {count}")
        
        # Get recent executions
        cursor.execute("""
            SELECT bot_name, timestamp, success 
            FROM bot_executions 
            WHERE timestamp > datetime('now', '-1 day')
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        rows = cursor.fetchall()
        
        if rows:
            print(f"\n    Recent bot executions:")
            for row in rows:
                status = "[OK]" if row[2] else "[FAIL]"
                print(f"      {status} {row[0]} at {row[1]}")
        else:
            print(f"    No recent executions found")
        
        conn.close()
    except Exception as e:
        print(f"    Error reading database: {e}")
else:
    print(f"    Database not found - data collection may not have started yet")
print()

# Check workflow database
workflow_db = installation_dir / "AI" / "intelligence" / "workflow_database.db"
print(f"[2] Checking Workflow Database...")
print(f"    Location: {workflow_db}")
print(f"    Exists: {workflow_db.exists()}")
print()

if workflow_db.exists():
    try:
        conn = sqlite3.connect(workflow_db)
        cursor = conn.cursor()
        
        # Check workflow records
        cursor.execute("""
            SELECT COUNT(*) FROM workflow_executions 
            WHERE execution_time > datetime('now', '-1 day')
        """)
        count = cursor.fetchone()[0]
        print(f"    Workflow records in last 24 hours: {count}")
        
        # Get recent records
        cursor.execute("""
            SELECT bot_name, execution_time 
            FROM workflow_executions 
            WHERE execution_time > datetime('now', '-1 day')
            ORDER BY execution_time DESC 
            LIMIT 10
        """)
        rows = cursor.fetchall()
        
        if rows:
            print(f"\n    Recent workflow records:")
            for row in rows:
                print(f"      - {row[0]} at {row[1]}")
        else:
            print(f"    No recent workflow records found")
        
        conn.close()
    except Exception as e:
        print(f"    Error reading database: {e}")
else:
    print(f"    Database not found - workflow recording may not have started yet")
print()

# Check centralized data
central_db = installation_dir / "_centralized_data" / "centralized_data.db"
print(f"[3] Checking Centralized Data Database...")
print(f"    Location: {central_db}")
print(f"    Exists: {central_db.exists()}")
print()

if central_db.exists():
    try:
        conn = sqlite3.connect(central_db)
        cursor = conn.cursor()
        
        # Check aggregated bot executions
        cursor.execute("SELECT COUNT(*) FROM aggregated_bot_executions")
        count = cursor.fetchone()[0]
        print(f"    Total aggregated bot executions: {count}")
        
        # Get recent aggregated executions
        cursor.execute("""
            SELECT bot_name, execution_timestamp 
            FROM aggregated_bot_executions 
            ORDER BY execution_timestamp DESC 
            LIMIT 10
        """)
        rows = cursor.fetchall()
        
        if rows:
            print(f"\n    Recent aggregated executions:")
            for row in rows:
                print(f"      - {row[0]} at {row[1]}")
        
        conn.close()
    except Exception as e:
        print(f"    Error reading database: {e}")
else:
    print(f"    Database not found - data centralization may not have started yet")
print()

# Check AI insights
insights_dir = installation_dir / "AI" / "intelligence"
print(f"[4] Checking AI Insights...")
print(f"    Location: {insights_dir}")
print(f"    Exists: {insights_dir.exists()}")
print()

if insights_dir.exists():
    insights_files = list(insights_dir.glob("insights_*.json"))
    print(f"    Insights files found: {len(insights_files)}")
    
    if insights_files:
        latest = max(insights_files, key=lambda p: p.stat().st_mtime)
        print(f"    Latest insights file: {latest.name}")
        print(f"    Modified: {datetime.fromtimestamp(latest.stat().st_mtime)}")
else:
    print(f"    Insights directory not found")
print()

# Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print()

secure_count = 0
workflow_count = 0
central_count = 0

if secure_db.exists():
    try:
        conn = sqlite3.connect(secure_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bot_executions WHERE timestamp > datetime('now', '-1 day')")
        secure_count = cursor.fetchone()[0]
        conn.close()
    except:
        pass

if workflow_db.exists():
    try:
        conn = sqlite3.connect(workflow_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM workflow_executions WHERE execution_time > datetime('now', '-1 day')")
        workflow_count = cursor.fetchone()[0]
        conn.close()
    except:
        pass

if central_db.exists():
    try:
        conn = sqlite3.connect(central_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM aggregated_bot_executions")
        central_count = cursor.fetchone()[0]
        conn.close()
    except:
        pass

print(f"[OK] Secure Collection: {secure_count} bot executions (last 24 hours)")
print(f"[OK] Workflow Recording: {workflow_count} workflow records (last 24 hours)")
print(f"[OK] Centralized Data: {central_count} total aggregated executions")
print()

if secure_count > 0 or workflow_count > 0:
    print("[OK] DATA COLLECTION IS WORKING!")
else:
    print("[WARN] No data collected yet - this may be normal if:")
    print("   - Automation Hub was just opened")
    print("   - Bots were launched directly (not through Automation Hub)")
    print("   - Data collection needs a moment to initialize")

print()
print("=" * 70)

