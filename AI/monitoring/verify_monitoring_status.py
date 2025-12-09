#!/usr/bin/env python3
"""
Verify Monitoring Status - Quick diagnostic
Checks if monitoring is actually working and collecting data
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

def verify_monitoring_status():
    """Verify monitoring status and data collection"""
    print("=" * 70)
    print("MONITORING STATUS VERIFICATION")
    print("=" * 70)
    print()
    
    installation_dir = Path(__file__).parent.parent.parent
    
    # Check 1: Monitor instance
    print("CHECK 1: Monitor Instance")
    print("-" * 70)
    try:
        from full_system_monitor import get_full_monitor
        monitor = get_full_monitor(installation_dir, user_consent=True)
        
        print(f"[OK] Monitor instance created")
        print(f"     monitoring_active: {monitor.monitoring_active}")
        print(f"     session_id: {monitor.session_id}")
        
        if monitor.monitoring_active:
            print("[OK] Monitoring is ACTIVE")
        else:
            print("[WARN] Monitoring is INACTIVE (but this is OK if not started yet)")
    except Exception as e:
        print(f"[FAIL] Error getting monitor: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Check 2: Database existence
    print("CHECK 2: Database Existence")
    print("-" * 70)
    db_paths = [
        installation_dir / "_secure_data" / "full_monitoring" / "full_monitoring.db",
        installation_dir / "AI" / "data" / "full_monitoring" / "full_monitoring.db",
    ]
    
    db_path = None
    for path in db_paths:
        if path.exists():
            db_path = path
            print(f"[OK] Database found: {path}")
            break
    
    if not db_path:
        print("[WARN] Database not found - this is normal if monitoring hasn't run yet")
        print("       Expected locations:")
        for path in db_paths:
            print(f"         - {path}")
    else:
        # Check 3: Data in database
        print()
        print("CHECK 3: Data in Database")
        print("-" * 70)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Total counts
            cursor.execute("SELECT COUNT(*) FROM screen_recordings")
            screen_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM keyboard_input")
            keyboard_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mouse_activity")
            mouse_count = cursor.fetchone()[0]
            
            print(f"     Total Screens: {screen_count:,}")
            print(f"     Total Keyboard: {keyboard_count:,}")
            print(f"     Total Mouse: {mouse_count:,}")
            
            # Recent activity (last 2 minutes)
            cutoff = (datetime.now() - timedelta(minutes=2)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM screen_recordings WHERE timestamp > ?
            """, (cutoff,))
            recent_screens = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM keyboard_input WHERE timestamp > ?
            """, (cutoff,))
            recent_keyboard = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM mouse_activity WHERE timestamp > ?
            """, (cutoff,))
            recent_mouse = cursor.fetchone()[0]
            
            print()
            print(f"     Recent Screens (last 2 min): {recent_screens:,}")
            print(f"     Recent Keyboard (last 2 min): {recent_keyboard:,}")
            print(f"     Recent Mouse (last 2 min): {recent_mouse:,}")
            
            if recent_screens > 0 or recent_keyboard > 0 or recent_mouse > 0:
                print()
                print("[OK] Data is being collected RIGHT NOW!")
            else:
                print()
                print("[WARN] No recent data - monitoring may not be active")
            
            # Latest session
            cursor.execute("""
                SELECT DISTINCT session_id, MAX(timestamp) as last_time
                FROM screen_recordings
                GROUP BY session_id
                ORDER BY last_time DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            if result:
                session_id, last_time = result
                print()
                print(f"     Latest Session: {session_id}")
                print(f"     Last Activity: {last_time}")
                
                try:
                    last_dt = datetime.fromisoformat(last_time)
                    time_diff = (datetime.now() - last_dt).total_seconds()
                    print(f"     Time Since Last Activity: {time_diff:.1f} seconds")
                    
                    if time_diff < 120:  # 2 minutes
                        print("[OK] Recent activity detected - monitoring is likely active")
                    else:
                        print("[WARN] No recent activity - monitoring may be inactive")
                except:
                    pass
            
            conn.close()
        except Exception as e:
            print(f"[FAIL] Error checking database: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print()
    
    if db_path and recent_screens > 0:
        print("[OK] Monitoring is WORKING and collecting data!")
        print("     The status display may just need to refresh.")
        print("     Try clicking 'Refresh Now' in the Master AI Dashboard.")
    elif db_path:
        print("[WARN] Database exists but no recent data.")
        print("     Monitoring may have started but isn't recording yet.")
        print("     This is normal if monitoring just started.")
    else:
        print("[WARN] No database found.")
        print("     Monitoring may not have run yet.")
        print("     Start monitoring from the Master AI Dashboard.")
    
    print()
    input("Press ENTER to close...")
    
    return True


if __name__ == "__main__":
    verify_monitoring_status()

