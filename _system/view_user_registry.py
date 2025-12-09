#!/usr/bin/env python3
"""
Admin User Registry Viewer
View all registered users and their data.
Shows which employees are registered and which computers they're using.
"""

import os
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime
from typing import Optional

# Import user registration
try:
    from user_registration import UserRegistration
    USER_REGISTRATION_AVAILABLE = True
except ImportError:
    USER_REGISTRATION_AVAILABLE = False
    UserRegistration = None

# Import data centralization
try:
    from data_centralization import DataCentralization
    DATA_CENTRALIZATION_AVAILABLE = True
except ImportError:
    DATA_CENTRALIZATION_AVAILABLE = False
    DataCentralization = None


def view_user_registry():
    """View all registered users"""
    print("=" * 70)
    print("ADMIN USER REGISTRY VIEWER")
    print("=" * 70)
    
    # Get installation directory
    installation_dir = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")
    
    print(f"\n[DIR] Installation Directory: {installation_dir}")
    print(f"[OK] Directory exists: {installation_dir.exists()}\n")
    
    if not USER_REGISTRATION_AVAILABLE:
        print("[ERROR] User registration not available!")
        return
    
    # Initialize user registration
    user_reg = UserRegistration(installation_dir)
    
    # Get all registered users
    all_users = user_reg.get_all_users()
    
    print(f"[USERS] TOTAL REGISTERED USERS: {len(all_users)}\n")
    
    if not all_users:
        print("[WARN] No users registered yet.")
        print("\nTo register users:")
        print("  1. Have employees run 'install_bots.bat'")
        print("  2. They will enter their name")
        print("  3. They will appear in this registry\n")
        return
    
    # Display all users
    print("=" * 70)
    print("REGISTERED USERS")
    print("=" * 70)
    
    for i, user in enumerate(all_users, 1):
        print(f"\n{i}. {user['user_name']}")
        print(f"   User Hash: {user['user_hash'][:16]}... (HIPAA-compliant)")
        print(f"   Computer: {user['computer_name']}")
        print(f"   Computer ID: {user['computer_id']}")
        print(f"   Registered: {user['registered_at']}")
        print(f"   Last Active: {user.get('last_active', 'Never')}")
    
    # Get all computers
    all_computers = user_reg.get_all_computers()
    
    print("\n" + "=" * 70)
    print(f"[COMPUTERS] TOTAL REGISTERED COMPUTERS: {len(all_computers)}")
    print("=" * 70)
    
    if all_computers:
        for i, computer in enumerate(all_computers, 1):
            print(f"\n{i}. {computer['computer_name']}")
            print(f"   Computer ID: {computer['computer_id']}")
            print(f"   Registered: {computer['registered_at']}")
            print(f"   Last Sync: {computer.get('last_sync', 'Never')}")
    
    # Get local user
    local_user = user_reg.get_local_user()
    
    print("\n" + "=" * 70)
    print("YOUR REGISTRATION")
    print("=" * 70)
    
    if local_user:
        print(f"\n[OK] You are registered as: {local_user['user_name']}")
        print(f"  Computer: {local_user['computer_name']}")
        print(f"  Computer ID: {local_user['computer_id']}")
        print(f"  Registered: {local_user['registered_at']}")
    else:
        print("\n[WARN] You are not registered yet.")
        print("  Run 'install_bots.bat' to register yourself.")
    
    # View aggregated data
    if DATA_CENTRALIZATION_AVAILABLE:
        print("\n" + "=" * 70)
        print("CENTRALIZED DATA STATISTICS")
        print("=" * 70)
        
        centralizer = DataCentralization(installation_dir)
        
        try:
            stats = centralizer.get_aggregated_data_for_training()
            print(f"\n[STATS] Aggregated Data:")
            print(f"  Bot Executions: {stats.get('bot_executions', 0)}")
            print(f"  AI Prompts: {stats.get('ai_prompts', 0)}")
            print(f"  Workflow Patterns: {stats.get('workflow_patterns', 0)}")
            print(f"  Unique Users: {stats.get('unique_users', 0)}")
            print(f"  Unique Computers: {stats.get('unique_computers', 0)}")
            print(f"  Total Records: {stats.get('total_records', 0)}")
        except Exception as e:
            print(f"\n[WARN] Error getting stats: {e}")
            print("  Data will appear after users start using bots.")
    
    print("\n" + "=" * 70)
    print("VIEW COMPLETE")
    print("=" * 70)
    
    print("\n[TIPS] Tips:")
    print("  • Run this script anytime to see all registered users")
    print("  • Users appear here after they run 'install_bots.bat'")
    print("  • Data will aggregate as users use bots")
    print("  • All data is in OneDrive and syncs automatically\n")


def view_user_data(user_name: Optional[str] = None):
    """View specific user's data"""
    if not user_name:
        print("\nEnter user name to view their data:")
        user_name = input("User name: ").strip()
    
    if not user_name:
        print("[WARN] No user name provided")
        return
    
    installation_dir = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")
    
    if not DATA_CENTRALIZATION_AVAILABLE:
        print("[ERROR] Data centralization not available!")
        return
    
    centralizer = DataCentralization(installation_dir)
    
    # Get user hash
    import hashlib
    user_hash = hashlib.sha256(user_name.encode()).hexdigest()
    
    # Query centralized database
    central_db = installation_dir / "_centralized_data" / "centralized_data.db"
    
    if not central_db.exists():
        print(f"[WARN] No centralized data yet for {user_name}")
        print("  Data will appear after they use bots.")
        return
    
    conn = sqlite3.connect(central_db)
    cursor = conn.cursor()
    
    # Get bot executions
    cursor.execute("""
        SELECT COUNT(*) FROM aggregated_bot_executions
        WHERE user_hash = ?
    """, (user_hash,))
    bot_count = cursor.fetchone()[0]
    
    # Get AI prompts
    cursor.execute("""
        SELECT COUNT(*) FROM aggregated_ai_prompts
        WHERE user_hash = ?
    """, (user_hash,))
    prompt_count = cursor.fetchone()[0]
    
    # Get workflow patterns
    cursor.execute("""
        SELECT COUNT(*) FROM aggregated_workflow_patterns
        WHERE user_hash = ?
    """, (user_hash,))
    pattern_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n[STATS] Data for {user_name}:")
    print(f"  Bot Executions: {bot_count}")
    print(f"  AI Prompts: {prompt_count}")
    print(f"  Workflow Patterns: {pattern_count}")
    print(f"  Total Records: {bot_count + prompt_count + pattern_count}")


def main():
    """Main function"""
    view_user_registry()
    
    # Option to view specific user data
    print("\nWould you like to view data for a specific user? (y/n): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        view_user_data()
    
    input("\nPress ENTER to close...")


if __name__ == "__main__":
    main()

