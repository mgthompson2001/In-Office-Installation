#!/usr/bin/env python3
"""
View Diagnostic Results
View real-time diagnostic results from automatic diagnostic monitoring.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import time

# Get installation directory
_current_file = Path(__file__).resolve()
if "In-Office Installation" in str(_current_file):
    installation_dir = _current_file.parent.parent
else:
    installation_dir = Path.cwd()
    if "_bots" in str(installation_dir):
        installation_dir = installation_dir.parent

secure_data_dir = installation_dir / "_secure_data"
log_file = secure_data_dir / "diagnostic_monitor.log"

def view_diagnostic_summary():
    """View diagnostic summary"""
    print("=" * 70)
    print("Browser Monitoring Diagnostic Summary")
    print("=" * 70)
    print()
    
    # Check database
    db_path = secure_data_dir / "browser_activity.db"
    if not db_path.exists():
        print("[WARN] Database not found - monitoring may not be active")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check recent sessions
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        cursor.execute("""
            SELECT COUNT(*), MAX(start_time)
            FROM session_summaries
            WHERE start_time > ?
        """, (one_hour_ago,))
        result = cursor.fetchone()
        recent_sessions = result[0] if result else 0
        last_session = result[1] if result and result[1] else None
        
        print(f"Recent Sessions (last hour): {recent_sessions}")
        if last_session:
            print(f"Last Session: {last_session}")
        print()
        
        # Check recent events
        five_minutes_ago = (datetime.now() - timedelta(minutes=5)).isoformat()
        
        cursor.execute("""
            SELECT COUNT(*), MAX(timestamp)
            FROM page_navigations
            WHERE timestamp > ?
        """, (five_minutes_ago,))
        nav_result = cursor.fetchone()
        recent_navs = nav_result[0] if nav_result else 0
        last_nav = nav_result[1] if nav_result and nav_result[1] else None
        
        cursor.execute("""
            SELECT COUNT(*), MAX(timestamp)
            FROM element_interactions
            WHERE timestamp > ?
        """, (five_minutes_ago,))
        element_result = cursor.fetchone()
        recent_elements = element_result[0] if element_result else 0
        last_element = element_result[1] if element_result and element_result[1] else None
        
        print(f"Recent Events (last 5 minutes):")
        print(f"  - Page Navigations: {recent_navs}")
        print(f"  - Element Interactions: {recent_elements}")
        print(f"  - Total: {recent_navs + recent_elements}")
        
        if last_nav or last_element:
            last_event = max(
                last_nav or "",
                last_element or ""
            )
            print(f"  - Last Event: {last_event}")
        else:
            print(f"  - Last Event: None (no events recorded)")
        print()
        
        # Check total events
        cursor.execute("SELECT COUNT(*) FROM page_navigations")
        total_navs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM element_interactions")
        total_elements = cursor.fetchone()[0]
        
        print(f"Total Events (all time):")
        print(f"  - Page Navigations: {total_navs}")
        print(f"  - Element Interactions: {total_elements}")
        print(f"  - Total: {total_navs + total_elements}")
        print()
        
        # Status
        if recent_navs + recent_elements > 0:
            print("[OK] Events are being recorded!")
        else:
            print("[WARN] No recent events recorded - monitoring may not be working")
        
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Could not check database: {e}")
    
    print()
    
    # Check diagnostic log
    if log_file.exists():
        print("=" * 70)
        print("Recent Diagnostic Log Entries")
        print("=" * 70)
        print()
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                recent_lines = lines[-20:] if len(lines) > 20 else lines
                
                for line in recent_lines:
                    if 'WARN' in line or 'ERROR' in line or 'WARNING' in line:
                        print(f"[ALERT] {line.strip()}")
                    elif 'INFO' in line and ('diagnostic' in line.lower() or 'event' in line.lower()):
                        print(f"[INFO] {line.strip()}")
        except Exception as e:
            print(f"[ERROR] Could not read log file: {e}")
    else:
        print("[WARN] Diagnostic log file not found")
    
    print()
    print("=" * 70)
    print("To view full diagnostic log:")
    print(f"  {log_file}")
    print("=" * 70)


def view_live_diagnostics(interval: int = 10):
    """View live diagnostic updates"""
    print("=" * 70)
    print("Live Diagnostic Monitoring")
    print("=" * 70)
    print("Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            # Clear screen (works on Windows)
            import os
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 70)
            print(f"Live Diagnostic Monitoring - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 70)
            print()
            
            view_diagnostic_summary()
            
            print()
            print(f"Refreshing in {interval} seconds... (Press Ctrl+C to stop)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
        print("Stopped live monitoring")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="View diagnostic results")
    parser.add_argument(
        "--live",
        action="store_true",
        help="View live diagnostic updates (refreshes every 10 seconds)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Refresh interval in seconds (default: 10)"
    )
    
    args = parser.parse_args()
    
    if args.live:
        view_live_diagnostics(interval=args.interval)
    else:
        view_diagnostic_summary()

