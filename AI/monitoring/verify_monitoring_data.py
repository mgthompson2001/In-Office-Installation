#!/usr/bin/env python3
"""
Verify Monitoring Data - Check if Full System Monitoring is Recording
This script verifies that monitoring is actually recording data.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_system"))
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_installation_dir():
    """Get installation directory"""
    return Path(__file__).parent.parent.parent

def check_monitoring_database():
    """Check if monitoring database exists and has data"""
    installation_dir = get_installation_dir()
    
    # Check both possible locations
    db_paths = [
        installation_dir / "_secure_data" / "full_monitoring" / "full_monitoring.db",
        installation_dir / "AI" / "data" / "full_monitoring" / "full_monitoring.db",
    ]
    
    db_path = None
    for path in db_paths:
        if path.exists():
            db_path = path
            break
    
    if not db_path:
        print("=" * 70)
        print("MONITORING DATABASE NOT FOUND")
        print("=" * 70)
        print("\nThe monitoring database does not exist at any expected location:")
        for path in db_paths:
            print(f"  • {path}")
        print("\nThis means monitoring has not been started yet, or data is not being saved.")
        print("\nTo start monitoring:")
        print("  1. Launch Full System Monitoring GUI")
        print("  2. Click 'Start Monitoring'")
        print("  3. Wait a few seconds and run this script again")
        return False
    
    print("=" * 70)
    print("MONITORING DATABASE FOUND")
    print("=" * 70)
    print(f"\nDatabase Location: {db_path}")
    print(f"Database Size: {db_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Check database contents
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\nTables Found: {', '.join(tables)}")
        
        # Check each table for data
        total_records = 0
        recent_records = 0
        cutoff_time = (datetime.now() - timedelta(minutes=5)).isoformat()
        
        print("\n" + "=" * 70)
        print("DATA SUMMARY")
        print("=" * 70)
        
        for table in tables:
            try:
                # Get total count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                total_records += count
                
                # Get recent count (last 5 minutes)
                if 'timestamp' in [desc[0] for desc in cursor.execute(f"PRAGMA table_info({table})").fetchall()]:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE timestamp > ?", (cutoff_time,))
                    recent = cursor.fetchone()[0]
                    recent_records += recent
                    
                    # Get latest timestamp
                    cursor.execute(f"SELECT MAX(timestamp) FROM {table}")
                    latest = cursor.fetchone()[0]
                    
                    print(f"\n{table.upper()}:")
                    print(f"  • Total Records: {count:,}")
                    print(f"  • Recent (last 5 min): {recent:,}")
                    if latest:
                        latest_dt = datetime.fromisoformat(latest)
                        age = datetime.now() - latest_dt
                        print(f"  • Latest Record: {latest_dt.strftime('%Y-%m-%d %H:%M:%S')} ({age.total_seconds():.0f} seconds ago)")
                    else:
                        print(f"  • Latest Record: None")
                else:
                    print(f"\n{table.upper()}:")
                    print(f"  • Total Records: {count:,}")
                    print(f"  • Recent (last 5 min): N/A (no timestamp column)")
            except Exception as e:
                print(f"\n{table.upper()}: Error - {e}")
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("MONITORING STATUS")
        print("=" * 70)
        
        if recent_records > 0:
            print(f"\n✅ MONITORING IS ACTIVE AND RECORDING")
            print(f"   • {recent_records:,} records in the last 5 minutes")
            print(f"   • Total records: {total_records:,}")
            print(f"\n   Your data is being recorded successfully!")
        elif total_records > 0:
            print(f"\n⚠️  MONITORING IS INACTIVE (but has historical data)")
            print(f"   • No records in the last 5 minutes")
            print(f"   • Total records: {total_records:,}")
            print(f"\n   Monitoring was active before but is not currently recording.")
            print(f"   Make sure Full System Monitoring GUI is running and 'Start' is clicked.")
        else:
            print(f"\n❌ MONITORING DATABASE EXISTS BUT HAS NO DATA")
            print(f"   • Database file exists but contains no records")
            print(f"\n   This could mean:")
            print(f"   • Monitoring was started but not recording")
            print(f"   • Dependencies are missing (mss, pynput, psutil, watchdog)")
            print(f"   • Check the monitoring log for errors")
        
        return recent_records > 0
        
    except Exception as e:
        print(f"\n❌ ERROR READING DATABASE: {e}")
        return False

def check_monitoring_log():
    """Check monitoring log for errors"""
    installation_dir = get_installation_dir()
    
    log_paths = [
        installation_dir / "_secure_data" / "full_monitoring" / "monitoring.log",
        installation_dir / "AI" / "data" / "full_monitoring" / "monitoring.log",
        installation_dir / "_system" / "full_monitoring.log",
    ]
    
    log_path = None
    for path in log_paths:
        if path.exists():
            log_path = path
            break
    
    if not log_path:
        print("\n" + "=" * 70)
        print("MONITORING LOG NOT FOUND")
        print("=" * 70)
        print("\nNo monitoring log file found. This is normal if monitoring hasn't been started.")
        return
    
    print("\n" + "=" * 70)
    print("MONITORING LOG (Last 20 Lines)")
    print("=" * 70)
    print(f"\nLog Location: {log_path}")
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            # Show last 20 lines
            for line in lines[-20:]:
                print(line.rstrip())
    except Exception as e:
        print(f"Error reading log: {e}")

def check_dependencies():
    """Check if monitoring dependencies are installed"""
    print("\n" + "=" * 70)
    print("DEPENDENCY CHECK")
    print("=" * 70)
    
    dependencies = {
        "mss": "Screen recording",
        "pynput": "Keyboard/Mouse monitoring",
        "psutil": "Application monitoring",
        "watchdog": "File system monitoring",
        "PIL (Pillow)": "Image processing",
        "cryptography": "Data encryption"
    }
    
    all_available = True
    for dep, purpose in dependencies.items():
        try:
            if dep == "PIL (Pillow)":
                import PIL
                print(f"✅ {dep:20s} - {purpose}")
            elif dep == "cryptography":
                import cryptography
                print(f"✅ {dep:20s} - {purpose}")
            else:
                __import__(dep)
                print(f"✅ {dep:20s} - {purpose}")
        except ImportError:
            print(f"❌ {dep:20s} - {purpose} (NOT INSTALLED)")
            all_available = False
    
    if not all_available:
        print("\n⚠️  Some dependencies are missing. Monitoring may not work fully.")
        print("   Run: pip install mss pynput psutil watchdog pillow cryptography")
    else:
        print("\n✅ All dependencies are installed!")
    
    return all_available

def main():
    """Main verification function"""
    print("\n" + "=" * 70)
    print("FULL SYSTEM MONITORING - DATA VERIFICATION")
    print("=" * 70)
    print("\nThis script verifies that monitoring is actually recording data.")
    print("Run this after starting Full System Monitoring to confirm it's working.\n")
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check database
    is_active = check_monitoring_database()
    
    # Check log
    check_monitoring_log()
    
    # Final summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    if is_active:
        print("\n✅ MONITORING IS WORKING CORRECTLY")
        print("   Data is being recorded in real-time.")
    elif deps_ok:
        print("\n⚠️  MONITORING IS NOT CURRENTLY RECORDING")
        print("   Dependencies are installed, but no recent data found.")
        print("   Make sure:")
        print("   1. Full System Monitoring GUI is open")
        print("   2. 'Start Monitoring' button is clicked")
        print("   3. You are actively using your computer")
    else:
        print("\n❌ MONITORING CANNOT WORK - DEPENDENCIES MISSING")
        print("   Install missing dependencies first.")
    
    print("\n" + "=" * 70)
    input("\nPress ENTER to close...")

if __name__ == "__main__":
    main()

