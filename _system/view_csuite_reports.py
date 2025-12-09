#!/usr/bin/env python3
"""
Quick script to view C-Suite reports
Run this to see all your C-Suite reports
"""

from pathlib import Path
import json
from csuite_ai_modules import CSuiteAIModules

def main():
    """View C-Suite reports"""
    installation_dir = Path(__file__).parent.parent
    csuite = CSuiteAIModules(installation_dir)
    
    print("=" * 70)
    print("C-Suite Reports Viewer")
    print("=" * 70)
    
    # Generate finance report
    print("\n📊 Generating Finance Report...")
    try:
        finance_report = csuite.generate_finance_report("monthly")
        print("\nFinance Report:")
        print(json.dumps(finance_report, indent=2))
    except Exception as e:
        print(f"Error generating finance report: {e}")
    
    # Monitor performance
    print("\n\n👥 Monitoring Employee Performance...")
    try:
        performance = csuite.monitor_employee_performance(30)
        print("\nEmployee Performance:")
        print(json.dumps(performance, indent=2))
    except Exception as e:
        print(f"Error monitoring performance: {e}")
    
    # Analyze patterns
    print("\n\n📈 Analyzing Data Patterns...")
    try:
        analytics = csuite.analyze_data_patterns()
        print("\nData Analytics:")
        print(json.dumps(analytics, indent=2))
    except Exception as e:
        print(f"Error analyzing patterns: {e}")
    
    print("\n" + "=" * 70)
    print("Reports saved to: _ai_intelligence/csuite_reports/")
    print("=" * 70)
    
    input("\nPress ENTER to close...")

if __name__ == "__main__":
    main()

