#!/usr/bin/env python3
"""
Admin Dashboard - View Employee Registry and Collected Data
Comprehensive tool for administrators to review employee data.
"""

import os
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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


class AdminDashboard:
    """Admin dashboard for viewing employee data"""
    
    def __init__(self, installation_dir: Path):
        self.installation_dir = installation_dir
        self.user_reg = None
        self.centralizer = None
        
        if USER_REGISTRATION_AVAILABLE:
            self.user_reg = UserRegistration(installation_dir)
        
        if DATA_CENTRALIZATION_AVAILABLE:
            self.centralizer = DataCentralization(installation_dir)
    
    def view_all_employees(self) -> List[Dict]:
        """View all registered employees"""
        if not self.user_reg:
            return []
        
        return self.user_reg.get_all_users()
    
    def view_employee_data(self, user_name: str) -> Dict:
        """View detailed data for a specific employee"""
        if not self.user_reg or not self.centralizer:
            return {}
        
        # Get user info
        all_users = self.user_reg.get_all_users()
        user_info = next((u for u in all_users if u['user_name'] == user_name), None)
        
        if not user_info:
            return {}
        
        # Get user hash
        import hashlib
        user_hash = hashlib.sha256(user_name.encode()).hexdigest()
        
        # Get data from centralized database
        central_db = self.installation_dir / "_centralized_data" / "centralized_data.db"
        
        if not central_db.exists():
            return {
                'user_info': user_info,
                'bot_executions': [],
                'ai_prompts': [],
                'workflow_patterns': [],
                'stats': {
                    'bot_executions': 0,
                    'ai_prompts': 0,
                    'workflow_patterns': 0,
                    'total_records': 0
                }
            }
        
        conn = sqlite3.connect(central_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get bot executions
        cursor.execute("""
            SELECT bot_name, execution_time, parameters, result
            FROM aggregated_bot_executions
            WHERE user_hash = ?
            ORDER BY execution_time DESC
            LIMIT 100
        """, (user_hash,))
        bot_executions = [dict(row) for row in cursor.fetchall()]
        
        # Get AI prompts
        cursor.execute("""
            SELECT prompt, response, execution_time, bot_used
            FROM aggregated_ai_prompts
            WHERE user_hash = ?
            ORDER BY execution_time DESC
            LIMIT 100
        """, (user_hash,))
        ai_prompts = [dict(row) for row in cursor.fetchall()]
        
        # Get workflow patterns
        cursor.execute("""
            SELECT pattern_name, pattern_data, frequency, last_used
            FROM aggregated_workflow_patterns
            WHERE user_hash = ?
            ORDER BY frequency DESC
            LIMIT 100
        """, (user_hash,))
        workflow_patterns = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'user_info': user_info,
            'bot_executions': bot_executions,
            'ai_prompts': ai_prompts,
            'workflow_patterns': workflow_patterns,
            'stats': {
                'bot_executions': len(bot_executions),
                'ai_prompts': len(ai_prompts),
                'workflow_patterns': len(workflow_patterns),
                'total_records': len(bot_executions) + len(ai_prompts) + len(workflow_patterns)
            }
        }
    
    def view_all_data_summary(self) -> Dict:
        """View summary of all collected data"""
        if not self.centralizer:
            return {}
        
        try:
            stats = self.centralizer.get_aggregated_data_for_training()
            return stats
        except Exception as e:
            print(f"[WARN] Error getting stats: {e}")
            return {}


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_employee_list(employees: List[Dict]):
    """Print list of employees"""
    if not employees:
        print("\n[WARN] No employees registered yet.")
        print("\nTo register employees:")
        print("  1. Have employees run 'install_bots.bat'")
        print("  2. They will enter their name")
        print("  3. They will appear in this registry\n")
        return
    
    print(f"\n[USERS] TOTAL REGISTERED EMPLOYEES: {len(employees)}\n")
    
    for i, emp in enumerate(employees, 1):
        print(f"{i}. {emp['user_name']}")
        print(f"   Computer: {emp['computer_name']}")
        print(f"   Computer ID: {emp['computer_id']}")
        print(f"   Registered: {emp['registered_at']}")
        print(f"   Last Active: {emp.get('last_active', 'Never')}")
        print()


def print_employee_details(employee_data: Dict):
    """Print detailed employee data"""
    if not employee_data:
        print("[WARN] No data found for this employee.")
        return
    
    user_info = employee_data.get('user_info', {})
    stats = employee_data.get('stats', {})
    bot_executions = employee_data.get('bot_executions', [])
    ai_prompts = employee_data.get('ai_prompts', [])
    workflow_patterns = employee_data.get('workflow_patterns', [])
    
    # User info
    print_header("EMPLOYEE INFORMATION")
    print(f"Name: {user_info.get('user_name', 'N/A')}")
    print(f"Computer: {user_info.get('computer_name', 'N/A')}")
    print(f"Computer ID: {user_info.get('computer_id', 'N/A')}")
    print(f"Registered: {user_info.get('registered_at', 'N/A')}")
    print(f"Last Active: {user_info.get('last_active', 'Never')}")
    
    # Statistics
    print_header("DATA STATISTICS")
    print(f"Bot Executions: {stats.get('bot_executions', 0)}")
    print(f"AI Prompts: {stats.get('ai_prompts', 0)}")
    print(f"Workflow Patterns: {stats.get('workflow_patterns', 0)}")
    print(f"Total Records: {stats.get('total_records', 0)}")
    
    # Bot Executions
    if bot_executions:
        print_header(f"RECENT BOT EXECUTIONS ({len(bot_executions)} shown)")
        for i, exec in enumerate(bot_executions[:10], 1):  # Show last 10
            print(f"\n{i}. Bot: {exec.get('bot_name', 'N/A')}")
            print(f"   Time: {exec.get('execution_time', 'N/A')}")
            if exec.get('parameters'):
                try:
                    params = json.loads(exec['parameters']) if isinstance(exec['parameters'], str) else exec['parameters']
                    print(f"   Parameters: {params}")
                except:
                    print(f"   Parameters: {exec.get('parameters', 'N/A')}")
            if exec.get('result'):
                print(f"   Result: {exec.get('result', 'N/A')}")
    
    # AI Prompts
    if ai_prompts:
        print_header(f"RECENT AI PROMPTS ({len(ai_prompts)} shown)")
        for i, prompt in enumerate(ai_prompts[:10], 1):  # Show last 10
            print(f"\n{i}. Time: {prompt.get('execution_time', 'N/A')}")
            print(f"   Prompt: {prompt.get('prompt', 'N/A')[:100]}...")
            if prompt.get('bot_used'):
                print(f"   Bot Used: {prompt.get('bot_used', 'N/A')}")
    
    # Workflow Patterns
    if workflow_patterns:
        print_header(f"WORKFLOW PATTERNS ({len(workflow_patterns)} shown)")
        for i, pattern in enumerate(workflow_patterns[:10], 1):  # Show last 10
            print(f"\n{i}. Pattern: {pattern.get('pattern_name', 'N/A')}")
            print(f"   Frequency: {pattern.get('frequency', 0)}")
            print(f"   Last Used: {pattern.get('last_used', 'N/A')}")


def main():
    """Main function"""
    print_header("ADMIN DASHBOARD - Employee Registry & Data Review")
    
    # Get installation directory
    installation_dir = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")
    
    print(f"\n[DIR] Installation Directory: {installation_dir}")
    print(f"[OK] Directory exists: {installation_dir.exists()}\n")
    
    if not USER_REGISTRATION_AVAILABLE:
        print("[ERROR] User registration not available!")
        input("\nPress ENTER to close...")
        return
    
    # Initialize dashboard
    dashboard = AdminDashboard(installation_dir)
    
    # View all employees
    employees = dashboard.view_all_employees()
    print_header("REGISTERED EMPLOYEES")
    print_employee_list(employees)
    
    if not employees:
        input("\nPress ENTER to close...")
        return
    
    # View summary statistics
    print_header("ALL DATA SUMMARY")
    summary = dashboard.view_all_data_summary()
    if summary:
        print(f"\n[STATS] Aggregated Data Across All Employees:")
        print(f"  Bot Executions: {summary.get('bot_executions', 0)}")
        print(f"  AI Prompts: {summary.get('ai_prompts', 0)}")
        print(f"  Workflow Patterns: {summary.get('workflow_patterns', 0)}")
        print(f"  Unique Users: {summary.get('unique_users', 0)}")
        print(f"  Unique Computers: {summary.get('unique_computers', 0)}")
        print(f"  Total Records: {summary.get('total_records', 0)}")
    else:
        print("\n[WARN] No aggregated data yet.")
        print("  Data will appear after employees start using bots.")
    
    # Option to view specific employee data
    print("\n" + "=" * 70)
    print("VIEW EMPLOYEE DATA")
    print("=" * 70)
    print("\nWould you like to view detailed data for a specific employee? (y/n): ", end="")
    
    try:
        response = input().strip().lower()
        
        if response == 'y':
            print("\nEnter employee name (or press ENTER to cancel): ", end="")
            employee_name = input().strip()
            
            if employee_name:
                print_header(f"DETAILED DATA FOR: {employee_name}")
                employee_data = dashboard.view_employee_data(employee_name)
                print_employee_details(employee_data)
    except (EOFError, KeyboardInterrupt):
        pass
    
    print("\n" + "=" * 70)
    print("DASHBOARD COMPLETE")
    print("=" * 70)
    print("\n[TIPS] Tips:")
    print("  • Run this script anytime to review employee data")
    print("  • Employees appear here after they run 'install_bots.bat'")
    print("  • Data updates automatically as employees use bots")
    print("  • All data is stored in OneDrive and syncs automatically")
    print("  • Database location: _centralized_data/centralized_data.db")
    print("  • Registry location: _user_directory/user_directory.db")
    
    input("\nPress ENTER to close...")


if __name__ == "__main__":
    main()

