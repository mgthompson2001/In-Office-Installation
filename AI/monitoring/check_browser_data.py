#!/usr/bin/env python3
"""
Check Browser Activity Data and AI Training Integration
"""

import sqlite3
import sys
from pathlib import Path

# Get installation directory
installation_dir = Path(__file__).parent.parent.parent
ai_dir = installation_dir / "AI"
secure_db_path = installation_dir / "_secure_data" / "browser_activity.db"
legacy_db_path = ai_dir / "data" / "browser_activity.db"
pattern_db_path = ai_dir / "intelligence" / "workflow_patterns.db"

# Ensure shared modules are importable
sys.path.insert(0, str(installation_dir / "_system"))

# Optional imports for deeper diagnostics
SecureDataCollector = None
LocalAITrainer = None
try:
    from secure_data_collector import SecureDataCollector  # type: ignore
except ImportError:
    SecureDataCollector = None

try:
    from local_ai_trainer import LocalAITrainer  # type: ignore
except ImportError:
    LocalAITrainer = None

print("=" * 60)
print("BROWSER ACTIVITY DATA & AI TRAINING STATUS")
print("=" * 60)
print()

# Check browser activity database
if secure_db_path.exists():
    active_db_path = secure_db_path
    print(f"[OK] Browser activity database found: {active_db_path}")
elif legacy_db_path.exists():
    active_db_path = legacy_db_path
    print(f"[WARN] Using legacy browser database: {active_db_path}")
    print("       (New captures now write to _secure_data/browser_activity.db)")
else:
    active_db_path = None

if not active_db_path:
    print("[INFO] Browser activity database does not exist yet.")
    print("       This means no browser activity has been recorded.")
    print()
else:
    print()
    
    try:
        conn = sqlite3.connect(active_db_path)
        cursor = conn.cursor()
        
        # Get table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"[INFO] Tables in database: {', '.join(tables)}")
        print()
        
        # Check page navigations
        if 'page_navigations' in tables:
            cursor.execute("SELECT COUNT(*) FROM page_navigations")
            nav_count = cursor.fetchone()[0]
            print(f"[DATA] Page navigations recorded: {nav_count}")
            
            if nav_count > 0:
                cursor.execute("SELECT MAX(timestamp) FROM page_navigations")
                latest = cursor.fetchone()[0]
                print(f"[DATA] Latest navigation: {latest}")
        else:
            print("[INFO] No page_navigations table found")
        
        # Check element interactions
        if 'element_interactions' in tables:
            cursor.execute("SELECT COUNT(*) FROM element_interactions")
            interact_count = cursor.fetchone()[0]
            print(f"[DATA] Element interactions recorded: {interact_count}")
        else:
            print("[INFO] No element_interactions table found")
        
        # Check sessions
        if 'sessions' in tables:
            cursor.execute("SELECT COUNT(*) FROM sessions")
            session_count = cursor.fetchone()[0]
            print(f"[DATA] Browser sessions recorded: {session_count}")
        else:
            print("[INFO] No sessions table found")
        
        conn.close()
        print()
        
    except Exception as e:
        print(f"[ERROR] Error reading database: {e}")
        print()

# Check pattern extraction database
if not pattern_db_path.exists():
    print("[INFO] Pattern extraction database does not exist yet.")
    print("       Patterns are extracted from browser activity data.")
    print()
else:
    print(f"[OK] Pattern extraction database found: {pattern_db_path}")
    print()
    
    try:
        conn = sqlite3.connect(pattern_db_path)
        cursor = conn.cursor()
        
        # Get table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"[INFO] Pattern tables: {', '.join(tables)}")
        
        # Check patterns
        if 'workflow_patterns' in tables:
            cursor.execute("SELECT COUNT(*) FROM workflow_patterns")
            pattern_count = cursor.fetchone()[0]
            print(f"[DATA] Workflow patterns extracted: {pattern_count}")
        
        conn.close()
        print()
        
    except Exception as e:
        print(f"[ERROR] Error reading pattern database: {e}")
        print()

# Check AI training integration
print("=" * 60)
print("AI TRAINING INTEGRATION")
print("=" * 60)
print()

if SecureDataCollector is None:
    print("[WARN] SecureDataCollector module not available; skipping integration check.")
else:
    print("[OK] SecureDataCollector module detected - browser capture starts automatically when bots launch from the Secure Launcher.")
    if LocalAITrainer is None:
        print("[WARN] LocalAITrainer module not available; skipping automated training status.")
    print()
    print("[INFO] Browser activity data is automatically:")
    print("       1. Recorded by browser_activity_monitor")
    print("       2. Processed by pattern_extraction_engine")
    print("       3. Fed to local_ai_trainer for model training")
    print("       4. Stored in _secure_data/browser_activity.db")
    print("       5. Patterns stored in AI/intelligence/workflow_patterns.db")

print()
print("=" * 60)

