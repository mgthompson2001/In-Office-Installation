#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to compare the merged Excel output with the Master Counselor List.
Excludes LOA and resigned counselors from the comparison.
"""

import pandas as pd
import os
import sys
import re

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

# File paths
master_file = r"G:\Company\Master Counselor\Master Counselor List.xlsx"
merged_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Final Merged - Complete.xlsx"

print("="*80)
print("COMPARING MERGED OUTPUT TO MASTER COUNSELOR LIST")
print("="*80)
print(f"\nMaster file: {os.path.basename(master_file)}")
print(f"Merged file: {os.path.basename(merged_file)}")
print("\n" + "="*80)

# Read Master Counselor List
print("\n1. Reading Master Counselor List...")
try:
    master_df = pd.read_excel(master_file)
    print(f"   [OK] Master List has {len(master_df)} rows")
    print(f"   [OK] Columns: {master_df.columns.tolist()}")
except Exception as e:
    print(f"   [ERROR] Error reading Master List: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Extract counselor names from Master List
print("\n2. Extracting counselors from Master List...")
master_counselor_names = set()

# Check for Last Name and First Name columns
if 'Last Name' in master_df.columns and 'First Name' in master_df.columns:
    for idx, row in master_df.iterrows():
        last_name = str(row.get('Last Name', '')).strip()
        first_name = str(row.get('First Name', '')).strip()
        
        # Skip empty or invalid rows
        if not last_name or not first_name or last_name.lower() == 'nan' or first_name.lower() == 'nan':
            continue
        
        # Skip KEY/instruction rows
        if any(keyword in last_name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
            continue
        if any(keyword in first_name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
            continue
        
        # Check for LOA (Leave of Absence) - check Notes column or any text columns
        is_loa = False
        is_resigned = False
        
        # Check Notes column
        if 'Notes' in master_df.columns:
            notes = str(row.get('Notes', '')).lower()
            if 'loa' in notes or 'leave of absence' in notes:
                is_loa = True
            if 'resigned' in notes or 'resign' in notes:
                is_resigned = True
        
        # Check if row is highlighted red (resigned) - we'll check fill color if available
        # For now, we'll rely on Notes column and text patterns
        
        # Check all text columns for LOA/resigned indicators
        for col in master_df.columns:
            cell_value = str(row.get(col, '')).lower()
            if 'loa' in cell_value or 'leave of absence' in cell_value:
                is_loa = True
            if 'resigned' in cell_value or 'resign' in cell_value:
                is_resigned = True
        
        # Skip LOA and resigned counselors
        if is_loa or is_resigned:
            continue
        
        counselor_name = f"{last_name}, {first_name}"
        master_counselor_names.add(counselor_name)

elif 'Counselor Name' in master_df.columns:
    for idx, row in master_df.iterrows():
        name = str(row.get('Counselor Name', '')).strip()
        if not name or name.lower() == 'nan':
            continue
        
        # Skip KEY/instruction rows
        if any(keyword in name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
            continue
        
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
        
        if is_loa or is_resigned:
            continue
        
        master_counselor_names.add(name)

print(f"   [OK] Found {len(master_counselor_names)} ACTIVE counselors in Master List (excluding LOA/resigned)")

# Read merged Excel
print("\n3. Reading merged Excel file...")
try:
    merged_df = pd.read_excel(merged_file)
    print(f"   [OK] Merged file has {len(merged_df)} rows")
except Exception as e:
    print(f"   [ERROR] Error reading merged file: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Extract counselor names from merged file
print("\n4. Extracting counselors from merged file...")
merged_counselor_names = set()

# Check for Counselor Name column
if 'Counselor Name' in merged_df.columns:
    for idx, row in merged_df.iterrows():
        name = str(row.get('Counselor Name', '')).strip()
        if name and name.lower() != 'nan':
            merged_counselor_names.add(name)
else:
    # Try to extract from counselor header rows (COUNSELOR: prefix)
    # Look for rows where first column starts with "COUNSELOR:"
    for idx, row in merged_df.iterrows():
        first_col = str(row.iloc[0] if len(row) > 0 else '').strip()
        if first_col.upper().startswith('COUNSELOR:'):
            name = first_col.replace('COUNSELOR:', '').strip()
            if name:
                merged_counselor_names.add(name)

print(f"   [OK] Found {len(merged_counselor_names)} unique counselors in merged file")

# Normalize names for comparison
def normalize_name(name):
    """Normalize name for comparison"""
    name = str(name).strip().lower()
    # Remove extra spaces
    name = ' '.join(name.split())
    # Handle comma-separated names
    if ',' in name:
        parts = [p.strip() for p in name.split(',')]
        if len(parts) >= 2:
            return f"{parts[0]}, {parts[1]}"
    return name

# Normalize both sets
master_normalized = {normalize_name(name): name for name in master_counselor_names}
merged_normalized = {normalize_name(name): name for name in merged_counselor_names}

# Find missing counselors
missing_counselors = []
for norm_name, orig_name in master_normalized.items():
    if norm_name not in merged_normalized:
        missing_counselors.append(orig_name)

# Find extra counselors (in merged but not in master)
extra_counselors = []
for norm_name, orig_name in merged_normalized.items():
    if norm_name not in master_normalized:
        extra_counselors.append(orig_name)

# Print results
print("\n" + "="*80)
print("COMPARISON RESULTS")
print("="*80)
print(f"\nExpected (active counselors in Master List): {len(master_counselor_names)}")
print(f"Found (in merged output): {len(merged_counselor_names)}")
print(f"Missing: {len(missing_counselors)}")
print(f"Extra (in merged but not in Master): {len(extra_counselors)}")

if missing_counselors:
    print(f"\nMISSING COUNSELORS ({len(missing_counselors)}):")
    for i, name in enumerate(sorted(missing_counselors), 1):
        print(f"  {i}. {name}")
else:
    print("\nSUCCESS: All active counselors from Master List were found in merged output!")

if extra_counselors:
    print(f"\nEXTRA COUNSELORS in merged output (not in Master List) ({len(extra_counselors)}):")
    for i, name in enumerate(sorted(extra_counselors)[:20], 1):
        print(f"  {i}. {name}")
    if len(extra_counselors) > 20:
        print(f"  ... and {len(extra_counselors) - 20} more")

# Calculate match rate
if len(master_counselor_names) > 0:
    match_rate = ((len(master_counselor_names) - len(missing_counselors)) / len(master_counselor_names)) * 100
    print(f"\nMatch Rate: {match_rate:.1f}% ({len(master_counselor_names) - len(missing_counselors)}/{len(master_counselor_names)})")

print("\n" + "="*80)

