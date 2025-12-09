#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to investigate the 30+ counselors in merged output that are NOT in Master Counselor List.
"""

import pandas as pd
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

# File paths
master_file = r"G:\Company\Master Counselor\Master Counselor List.xlsx"
merged_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Final Merged - Complete.xlsx"

# Original input files to check
input_files = [
    r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Merged - All Parts Combined.xlsx",
    r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Log for remaining Run\Final Missing\remainder.xlsx",
]

print("="*80)
print("INVESTIGATING EXTRA COUNSELORS NOT IN MASTER LIST")
print("="*80)

# Read Master Counselor List
print("\n1. Reading Master Counselor List...")
master_df = pd.read_excel(master_file)
master_counselor_names = set()
master_all_names = set()  # All names including LOA/resigned for comparison

if 'Last Name' in master_df.columns and 'First Name' in master_df.columns:
    for idx, row in master_df.iterrows():
        last_name = str(row.get('Last Name', '')).strip()
        first_name = str(row.get('First Name', '')).strip()
        
        if not last_name or not first_name or last_name.lower() == 'nan' or first_name.lower() == 'nan':
            continue
        
        if any(keyword in last_name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
            continue
        if any(keyword in first_name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
            continue
        
        counselor_name = f"{last_name}, {first_name}"
        master_all_names.add(counselor_name)  # Add to all names
        
        # Check for LOA/resigned
        is_loa = False
        is_resigned = False
        
        if 'Notes' in master_df.columns:
            notes = str(row.get('Notes', '')).lower()
            if 'loa' in notes or 'leave of absence' in notes:
                is_loa = True
            if 'resigned' in notes or 'resign' in notes:
                is_resigned = True
        
        for col in master_df.columns:
            cell_value = str(row.get(col, '')).lower()
            if 'loa' in cell_value or 'leave of absence' in cell_value:
                is_loa = True
            if 'resigned' in cell_value or 'resign' in cell_value:
                is_resigned = True
        
        # Only add to active list if not LOA/resigned
        if not is_loa and not is_resigned:
            master_counselor_names.add(counselor_name)

print(f"   [OK] Found {len(master_all_names)} total counselors in Master List")
print(f"   [OK] Found {len(master_counselor_names)} ACTIVE counselors (excluding LOA/resigned)")

# Read merged file
print("\n2. Reading merged output file...")
merged_df = pd.read_excel(merged_file)
merged_counselor_names = set()

if 'Counselor Name' in merged_df.columns:
    for idx, row in merged_df.iterrows():
        name = str(row.get('Counselor Name', '')).strip()
        if name and name.lower() != 'nan':
            merged_counselor_names.add(name)

print(f"   [OK] Found {len(merged_counselor_names)} counselors in merged output")

# Normalize names for comparison
def normalize_name(name):
    name = str(name).strip().lower()
    name = ' '.join(name.split())
    if ',' in name:
        parts = [p.strip() for p in name.split(',')]
        if len(parts) >= 2:
            return f"{parts[0]}, {parts[1]}"
    return name

# Normalize ALL master names (including LOA/resigned) for comparison
master_all_normalized = {normalize_name(name): name for name in master_all_names}
master_normalized = {normalize_name(name): name for name in master_counselor_names}
merged_normalized = {normalize_name(name): name for name in merged_counselor_names}

# Find extra counselors - NOT in Master List at all (including LOA/resigned)
extra_counselors = []
for norm_name, orig_name in merged_normalized.items():
    if norm_name not in master_all_normalized:  # Check against ALL names in Master List
        extra_counselors.append(orig_name)

print(f"\n3. Found {len(extra_counselors)} EXTRA counselors in merged output")

# Check which input files these counselors came from
print("\n4. Checking source files for each extra counselor...")
extra_counselor_details = []

for counselor_name in sorted(extra_counselors):
    details = {
        'counselor_name': counselor_name,
        'found_in_merged': True,
        'found_in_input_files': [],
        'client_count': 0
    }
    
    # Count clients for this counselor in merged file
    if 'Counselor Name' in merged_df.columns:
        client_rows = merged_df[merged_df['Counselor Name'].astype(str).str.strip() == counselor_name]
        details['client_count'] = len(client_rows)
    
    # Check each input file
    for input_file in input_files:
        if os.path.exists(input_file):
            try:
                input_df = pd.read_excel(input_file)
                if 'Counselor Name' in input_df.columns:
                    found = input_df['Counselor Name'].astype(str).str.strip().str.contains(counselor_name, case=False, na=False).any()
                    if found:
                        details['found_in_input_files'].append(os.path.basename(input_file))
            except Exception as e:
                pass
    
    extra_counselor_details.append(details)

# Print full list
print("\n" + "="*80)
print("COMPLETE LIST OF EXTRA COUNSELORS (NOT IN MASTER LIST)")
print("="*80)
print(f"\nTotal: {len(extra_counselors)} counselors\n")

for i, details in enumerate(extra_counselor_details, 1):
    print(f"{i:2d}. {details['counselor_name']}")
    print(f"     - Client count in merged output: {details['client_count']}")
    if details['found_in_input_files']:
        print(f"     - Found in input file(s): {', '.join(details['found_in_input_files'])}")
    else:
        print(f"     - WARNING: Not found in any input file (may have been added during merge)")
    print()

# Summary
print("="*80)
print("SUMMARY")
print("="*80)
print(f"\nTotal extra counselors: {len(extra_counselors)}")
print(f"Total clients for extra counselors: {sum(d['client_count'] for d in extra_counselor_details)}")

# Group by source
from_input1 = [d for d in extra_counselor_details if 'Merged - All Parts Combined.xlsx' in d['found_in_input_files']]
from_input2 = [d for d in extra_counselor_details if 'remainder.xlsx' in d['found_in_input_files']]
from_both = [d for d in extra_counselor_details if len(d['found_in_input_files']) > 1]
from_neither = [d for d in extra_counselor_details if len(d['found_in_input_files']) == 0]

print(f"\nSource breakdown:")
print(f"  - From 'Merged - All Parts Combined.xlsx': {len(from_input1)}")
print(f"  - From 'remainder.xlsx': {len(from_input2)}")
print(f"  - From both files: {len(from_both)}")
print(f"  - From neither (added during merge?): {len(from_neither)}")

if from_neither:
    print(f"\nWARNING: {len(from_neither)} counselors were NOT in any input file!")
    print("These may have been incorrectly added during the merge process.")

print("\n" + "="*80)
print("RECOMMENDATION:")
print("These counselors should be REMOVED from the output Excel as they are not")
print("in the Master Counselor List and should not have been processed.")
print("="*80)

