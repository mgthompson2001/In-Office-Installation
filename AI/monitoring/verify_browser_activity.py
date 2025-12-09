#!/usr/bin/env python3
"""
Verify Browser Activity Recording
Check if browser activity has been recorded after running bots.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add _system to path
system_dir = Path(__file__).parent
sys.path.insert(0, str(system_dir))

installation_dir = system_dir.parent

print("=" * 70)
print("Browser Activity Verification")
print("=" * 70)
print()

# Check browser activity database
db_path = installation_dir / "_secure_data" / "browser_activity.db"

if not db_path.exists():
    print("[INFO] Browser activity database does not exist yet.")
    print("       Run a bot first to create browser activity data.")
    print()
    sys.exit(0)

print(f"[OK] Database found: {db_path}")
print()

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check page navigations
    cursor.execute("SELECT COUNT(*) as count FROM page_navigations")
    page_count = cursor.fetchone()["count"]
    
    # Check element interactions
    cursor.execute("SELECT COUNT(*) as count FROM element_interactions")
    element_count = cursor.fetchone()["count"]
    
    # Check form field interactions
    cursor.execute("SELECT COUNT(*) as count FROM form_field_interactions")
    form_count = cursor.fetchone()["count"]
    
    # Check workflow patterns
    cursor.execute("SELECT COUNT(*) as count FROM workflow_patterns")
    pattern_count = cursor.fetchone()["count"]
    
    # Check session summaries
    cursor.execute("SELECT COUNT(*) as count FROM session_summaries")
    session_count = cursor.fetchone()["count"]
    
    print("Database Statistics:")
    print(f"  Page navigations: {page_count}")
    print(f"  Element interactions: {element_count}")
    print(f"  Form field interactions: {form_count}")
    print(f"  Workflow patterns: {pattern_count}")
    print(f"  Session summaries: {session_count}")
    print()
    
    if page_count == 0 and element_count == 0 and form_count == 0:
        print("[INFO] No browser activity recorded yet.")
        print("       This is expected if no bots have run since Phase 1 was implemented.")
        print()
        print("To test browser activity recording:")
        print("1. Open Automation Hub")
        print("2. Run a bot (e.g., Penelope Workflow Tool)")
        print("3. Run this script again to see recorded activity")
        print()
    else:
        print("[SUCCESS] Browser activity has been recorded!")
        print()
        
        # Show recent page navigations
        if page_count > 0:
            print("Recent Page Navigations:")
            cursor.execute("""
                SELECT timestamp, anonymized_url, page_title, domain
                FROM page_navigations
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            for row in cursor.fetchall():
                print(f"  [{row['timestamp']}] {row['domain']}")
                print(f"    URL: {row['anonymized_url']}")
                if row['page_title']:
                    print(f"    Title: {row['page_title']}")
                print()
        
        # Show recent element interactions
        if element_count > 0:
            print("Recent Element Interactions:")
            cursor.execute("""
                SELECT timestamp, action_type, element_tag, element_id, element_name
                FROM element_interactions
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            for row in cursor.fetchall():
                print(f"  [{row['timestamp']}] {row['action_type']}")
                if row['element_tag']:
                    print(f"    Tag: {row['element_tag']}")
                if row['element_id']:
                    print(f"    ID: {row['element_id']}")
                if row['element_name']:
                    print(f"    Name: {row['element_name']}")
                print()
        
        # Show session summaries
        if session_count > 0:
            print("Session Summaries:")
            cursor.execute("""
                SELECT session_id, bot_name, start_time, total_pages, total_actions
                FROM session_summaries
                ORDER BY start_time DESC
                LIMIT 5
            """)
            for row in cursor.fetchall():
                print(f"  Session: {row['session_id']}")
                if row['bot_name']:
                    print(f"    Bot: {row['bot_name']}")
                print(f"    Started: {row['start_time']}")
                print(f"    Pages: {row['total_pages']}, Actions: {row['total_actions']}")
                print()
    
    # Check pattern database
    pattern_db = installation_dir / "AI" / "intelligence" / "workflow_patterns.db"
    
    if pattern_db.exists():
        print("Pattern Extraction Database:")
        conn2 = sqlite3.connect(pattern_db)
        conn2.row_factory = sqlite3.Row
        cursor2 = conn2.cursor()
        
        cursor2.execute("SELECT COUNT(*) as count FROM extracted_patterns")
        extracted_count = cursor2.fetchone()["count"]
        
        cursor2.execute("SELECT COUNT(*) as count FROM pattern_sequences")
        sequence_count = cursor2.fetchone()["count"]
        
        print(f"  Extracted patterns: {extracted_count}")
        print(f"  Pattern sequences: {sequence_count}")
        print()
        
        if extracted_count > 0:
            print("Top Patterns by Frequency:")
            cursor2.execute("""
                SELECT pattern_type, frequency, last_seen
                FROM extracted_patterns
                ORDER BY frequency DESC
                LIMIT 5
            """)
            for row in cursor2.fetchall():
                print(f"  {row['pattern_type']}: {row['frequency']} times (last: {row['last_seen']})")
            print()
        
        conn2.close()
    
    conn.close()
    
    print("=" * 70)
    print("Verification Complete")
    print("=" * 70)

except Exception as e:
    print(f"[ERROR] Failed to check database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

