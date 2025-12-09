#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check the structure of the merged file to understand how counselors are represented.
"""

import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

merged_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Final Merged - Complete.xlsx"

print("Checking merged file structure...")
df = pd.read_excel(merged_file)

print(f"Total rows: {len(df)}")
print(f"Columns: {df.columns.tolist()}")

# Check first column for "COUNSELOR:" headers
print("\nChecking first column for COUNSELOR: headers...")
first_col = df.iloc[:, 0]
counselor_headers = first_col[first_col.astype(str).str.upper().str.startswith('COUNSELOR:')]
print(f"Found {len(counselor_headers)} rows starting with 'COUNSELOR:'")

# Check Counselor Name column
if 'Counselor Name' in df.columns:
    print("\nChecking Counselor Name column...")
    counselor_names = df['Counselor Name'].dropna().unique()
    print(f"Found {len(counselor_names)} unique counselor names in 'Counselor Name' column")
    print(f"\nFirst 10 counselor names:")
    for i, name in enumerate(counselor_names[:10], 1):
        count = len(df[df['Counselor Name'] == name])
        print(f"  {i}. {name} ({count} rows)")

# Check if there are rows where first column is COUNSELOR: but Counselor Name is different
print("\nChecking for mismatches...")
if 'Counselor Name' in df.columns:
    for idx, row in df.head(50).iterrows():
        first_val = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
        counselor_name = str(row.get('Counselor Name', '')) if pd.notna(row.get('Counselor Name')) else ""
        if first_val.upper().startswith('COUNSELOR:'):
            extracted = first_val.replace('COUNSELOR:', '').strip()
            if counselor_name and extracted != counselor_name:
                print(f"  Row {idx+2}: Header='{extracted}', Counselor Name='{counselor_name}'")

