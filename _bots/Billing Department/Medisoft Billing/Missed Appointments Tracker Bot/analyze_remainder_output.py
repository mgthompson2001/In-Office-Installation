#!/usr/bin/env python3
"""
Script to analyze the remainder output Excel and list all counselors found.
"""

import pandas as pd
import sys

# Output Excel file
output_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Log for remaining Run\Final Missing\remainder.xlsx"

print("Analyzing output Excel file...")
print("="*80)

try:
    # Read output Excel
    output_df = pd.read_excel(output_file)
    print(f"Total rows in output: {len(output_df)}")
    print(f"Columns: {output_df.columns.tolist()}\n")
    
    # Get unique counselors from output
    if 'Counselor Name' in output_df.columns:
        counselor_names = output_df['Counselor Name'].dropna().unique()
        counselor_names = [str(name).strip() for name in counselor_names if str(name).strip().lower() != 'nan']
        counselor_names = sorted(set(counselor_names))
        
        print(f"Found {len(counselor_names)} unique counselors in output:\n")
        for i, name in enumerate(counselor_names, 1):
            # Count how many clients each counselor has
            client_count = len(output_df[output_df['Counselor Name'].astype(str).str.strip() == name])
            print(f"  {i:2d}. {name} ({client_count} client(s))")
        
        # Also check if there are any rows without counselor names
        missing_counselor = output_df[output_df['Counselor Name'].isna() | (output_df['Counselor Name'].astype(str).str.strip() == 'nan')]
        if len(missing_counselor) > 0:
            print(f"\n⚠️  Warning: {len(missing_counselor)} rows have no counselor name")
        
        # Check for counselor header rows (bold rows that might indicate counselor sections)
        print(f"\n" + "="*80)
        print("SUMMARY:")
        print(f"  Total unique counselors found: {len(counselor_names)}")
        print(f"  Total rows (including clients): {len(output_df)}")
        
    else:
        print("ERROR: 'Counselor Name' column not found in output Excel")
        print("Available columns:", output_df.columns.tolist())
        
        # Try to find counselor information in other columns
        if 'Client Name' in output_df.columns:
            print("\nChecking 'Client Name' column for patterns...")
            client_names = output_df['Client Name'].dropna().unique()[:20]
            print("Sample client names:", client_names[:10])
    
except Exception as e:
    print(f"ERROR reading Excel file: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("Please compare this list with the input Excel file to verify all counselors were processed.")

