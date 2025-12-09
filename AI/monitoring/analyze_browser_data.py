#!/usr/bin/env python3
"""
Analyze Browser Activity Data
Shows detailed browser activity data recorded from bot runs.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import json

# Add _system to path
system_dir = Path(__file__).parent
sys.path.insert(0, str(system_dir))

installation_dir = system_dir.parent

print("=" * 70)
print("Browser Activity Data Analysis")
print("=" * 70)
print()

# Check browser activity database
db_path = installation_dir / "_secure_data" / "browser_activity.db"

if not db_path.exists():
    print("[INFO] Browser activity database does not exist yet.")
    print("       Run a bot first to create browser activity data.")
    sys.exit(0)

print(f"[OK] Database found: {db_path}")
print()

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get overall statistics
    cursor.execute("SELECT COUNT(*) as count FROM page_navigations")
    page_count = cursor.fetchone()["count"]
    
    cursor.execute("SELECT COUNT(*) as count FROM element_interactions")
    element_count = cursor.fetchone()["count"]
    
    cursor.execute("SELECT COUNT(*) as count FROM form_field_interactions")
    form_count = cursor.fetchone()["count"]
    
    cursor.execute("SELECT COUNT(*) as count FROM session_summaries")
    session_count = cursor.fetchone()["count"]
    
    print("=" * 70)
    print("OVERALL STATISTICS")
    print("=" * 70)
    print(f"Page Navigations: {page_count}")
    print(f"Element Interactions: {element_count}")
    print(f"Form Field Interactions: {form_count}")
    print(f"Session Summaries: {session_count}")
    print()
    
    if page_count == 0 and element_count == 0 and form_count == 0:
        print("[INFO] No browser activity recorded yet.")
        print("       Run a bot and then check again.")
        conn.close()
        sys.exit(0)
    
    # Show session summaries
    if session_count > 0:
        print("=" * 70)
        print("SESSION SUMMARIES")
        print("=" * 70)
        cursor.execute("""
            SELECT session_id, bot_name, start_time, end_time, total_pages, total_actions
            FROM session_summaries
            ORDER BY start_time DESC
        """)
        sessions = cursor.fetchall()
        for i, session in enumerate(sessions, 1):
            print(f"\nSession {i}:")
            print(f"  Session ID: {session['session_id']}")
            print(f"  Bot Name: {session['bot_name'] or 'Unknown'}")
            print(f"  Start Time: {session['start_time']}")
            print(f"  End Time: {session['end_time'] or 'Still active'}")
            print(f"  Total Pages: {session['total_pages']}")
            print(f"  Total Actions: {session['total_actions']}")
        print()
    
    # Show page navigations
    if page_count > 0:
        print("=" * 70)
        print("PAGE NAVIGATIONS (Last 20)")
        print("=" * 70)
        cursor.execute("""
            SELECT timestamp, session_id, anonymized_url, page_title, domain
            FROM page_navigations
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        pages = cursor.fetchall()
        for i, page in enumerate(pages, 1):
            print(f"\nNavigation {i}:")
            print(f"  Time: {page['timestamp']}")
            print(f"  Session: {page['session_id'] or 'Unknown'}")
            print(f"  Domain: {page['domain'] or 'Unknown'}")
            print(f"  URL: {page['anonymized_url']}")
            if page['page_title']:
                print(f"  Title: {page['page_title']}")
        print()
    
    # Show element interactions
    if element_count > 0:
        print("=" * 70)
        print("ELEMENT INTERACTIONS (Last 20)")
        print("=" * 70)
        cursor.execute("""
            SELECT timestamp, session_id, action_type, element_tag, element_id, element_name, element_type
            FROM element_interactions
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        elements = cursor.fetchall()
        for i, elem in enumerate(elements, 1):
            print(f"\nInteraction {i}:")
            print(f"  Time: {elem['timestamp']}")
            print(f"  Session: {elem['session_id'] or 'Unknown'}")
            print(f"  Action: {elem['action_type']}")
            if elem['element_tag']:
                print(f"  Tag: {elem['element_tag']}")
            if elem['element_id']:
                print(f"  ID: {elem['element_id']}")
            if elem['element_name']:
                print(f"  Name: {elem['element_name']}")
            if elem['element_type']:
                print(f"  Type: {elem['element_type']}")
        print()
    
    # Show form field interactions
    if form_count > 0:
        print("=" * 70)
        print("FORM FIELD INTERACTIONS (Last 20)")
        print("=" * 70)
        cursor.execute("""
            SELECT timestamp, session_id, field_name, field_id, field_type, has_value
            FROM form_field_interactions
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        fields = cursor.fetchall()
        for i, field in enumerate(fields, 1):
            print(f"\nForm Field {i}:")
            print(f"  Time: {field['timestamp']}")
            print(f"  Session: {field['session_id'] or 'Unknown'}")
            if field['field_name']:
                print(f"  Name: {field['field_name']}")
            if field['field_id']:
                print(f"  ID: {field['field_id']}")
            if field['field_type']:
                print(f"  Type: {field['field_type']}")
            print(f"  Has Value: {'Yes' if field['has_value'] else 'No'}")
        print()
    
    # Show workflow patterns
    cursor.execute("SELECT COUNT(*) as count FROM workflow_patterns")
    pattern_count = cursor.fetchone()["count"]
    
    if pattern_count > 0:
        print("=" * 70)
        print("WORKFLOW PATTERNS")
        print("=" * 70)
        cursor.execute("""
            SELECT pattern_hash, pattern_type, frequency, first_seen, last_seen
            FROM workflow_patterns
            ORDER BY frequency DESC
            LIMIT 10
        """)
        patterns = cursor.fetchall()
        for i, pattern in enumerate(patterns, 1):
            print(f"\nPattern {i}:")
            print(f"  Hash: {pattern['pattern_hash'][:16]}...")
            print(f"  Type: {pattern['pattern_type']}")
            print(f"  Frequency: {pattern['frequency']} times")
            print(f"  First Seen: {pattern['first_seen']}")
            print(f"  Last Seen: {pattern['last_seen']}")
        print()
    
    # Check pattern extraction database
    pattern_db = installation_dir / "AI" / "intelligence" / "workflow_patterns.db"
    
    if pattern_db.exists():
        print("=" * 70)
        print("PATTERN EXTRACTION DATABASE")
        print("=" * 70)
        conn2 = sqlite3.connect(pattern_db)
        conn2.row_factory = sqlite3.Row
        cursor2 = conn2.cursor()
        
        cursor2.execute("SELECT COUNT(*) as count FROM extracted_patterns")
        extracted_count = cursor2.fetchone()["count"]
        
        cursor2.execute("SELECT COUNT(*) as count FROM pattern_sequences")
        sequence_count = cursor2.fetchone()["count"]
        
        print(f"Extracted Patterns: {extracted_count}")
        print(f"Pattern Sequences: {sequence_count}")
        print()
        
        if extracted_count > 0:
            print("Top Patterns by Frequency:")
            cursor2.execute("""
                SELECT pattern_type, frequency, confidence_score, last_seen
                FROM extracted_patterns
                ORDER BY frequency DESC, confidence_score DESC
                LIMIT 10
            """)
            for row in cursor2.fetchall():
                print(f"  {row['pattern_type']}: {row['frequency']} times (confidence: {row['confidence_score']:.2f}, last: {row['last_seen']})")
            print()
        
        conn2.close()
    
    conn.close()
    
    print("=" * 70)
    print("Analysis Complete")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - {page_count} page navigations recorded")
    print(f"  - {element_count} element interactions recorded")
    print(f"  - {form_count} form field interactions recorded")
    print(f"  - {session_count} sessions recorded")
    print(f"  - {pattern_count} workflow patterns extracted")
    print()
    
    if page_count > 0 or element_count > 0 or form_count > 0:
        print("[SUCCESS] Browser activity monitoring is working correctly!")
        print("         Data has been recorded and is ready for AI training.")
    else:
        print("[INFO] No browser activity recorded yet.")

except Exception as e:
    print(f"[ERROR] Failed to analyze database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

