#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to find exact extra counselors by comparing raw names.
"""

import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# File paths
master_file = r"G:\Company\Master Counselor\Master Counselor List.xlsx"
merged_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Final Merged - Complete.xlsx"

print("="*80)
print("FINDING EXACT EXTRA COUNSELORS")
print("="*80)

# Read Master Counselor List - get ALL names (raw)
print("\n1. Reading Master Counselor List...")
master_df = pd.read_excel(master_file)
master_all_names_raw = set()

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
        master_all_names_raw.add(counselor_name)
        # Also add variations
        master_all_names_raw.add(f"{last_name}, {first_name.split()[0]}")  # First name only (no middle)
        if ' ' in first_name:
            master_all_names_raw.add(f"{last_name}, {first_name.split()[0]} {first_name.split()[-1]}")  # First and last part

print(f"   [OK] Found {len(master_all_names_raw)} counselor name variations in Master List")

# Read merged file - get ALL names (raw)
print("\n2. Reading merged output file...")
merged_df = pd.read_excel(merged_file)
merged_counselor_names_raw = set()

if 'Counselor Name' in merged_df.columns:
    for idx, row in merged_df.iterrows():
        name = str(row.get('Counselor Name', '')).strip()
        if name and name.lower() != 'nan':
            merged_counselor_names_raw.add(name)

print(f"   [OK] Found {len(merged_counselor_names_raw)} counselors in merged output")

# Compare with multiple normalization strategies
def normalize_name_v1(name):
    """Basic normalization"""
    name = str(name).strip().lower()
    name = ' '.join(name.split())
    if ',' in name:
        parts = [p.strip() for p in name.split(',')]
        if len(parts) >= 2:
            return f"{parts[0]}, {parts[1]}"
    return name

def normalize_name_v2(name):
    """Normalization with first name only"""
    name = str(name).strip().lower()
    name = ' '.join(name.split())
    if ',' in name:
        parts = [p.strip() for p in name.split(',')]
        if len(parts) >= 2:
            first_part = parts[1].split()[0] if parts[1] else ''
            return f"{parts[0]}, {first_part}"
    return name

# Try to find matches with different strategies
print("\n3. Comparing names with multiple strategies...")
extra_counselors = []
matched_counselors = set()

for merged_name in merged_counselor_names_raw:
    found_match = False
    
    # Strategy 1: Exact match
    if merged_name in master_all_names_raw:
        found_match = True
        matched_counselors.add(merged_name)
        continue
    
    # Strategy 2: Normalized match
    merged_norm = normalize_name_v1(merged_name)
    for master_name in master_all_names_raw:
        master_norm = normalize_name_v1(master_name)
        if merged_norm == master_norm:
            found_match = True
            matched_counselors.add(merged_name)
            break
    
    # Strategy 3: First name only match
    if not found_match:
        merged_norm2 = normalize_name_v2(merged_name)
        for master_name in master_all_names_raw:
            master_norm2 = normalize_name_v2(master_name)
            if merged_norm2 == master_norm2:
                found_match = True
                matched_counselors.add(merged_name)
                break
    
    if not found_match:
        extra_counselors.append(merged_name)

print(f"   [OK] Found {len(matched_counselors)} matched counselors")
print(f"   [OK] Found {len(extra_counselors)} EXTRA counselors (no match in Master List)")

# Print the extra counselors
print("\n" + "="*80)
print("EXTRA COUNSELORS (NOT IN MASTER LIST AT ALL)")
print("="*80)
print(f"\nTotal: {len(extra_counselors)} counselors\n")

if extra_counselors:
    for i, name in enumerate(sorted(extra_counselors), 1):
        # Count clients
        client_count = len(merged_df[merged_df['Counselor Name'].astype(str).str.strip() == name])
        print(f"{i:2d}. {name} ({client_count} client(s))")
else:
    print("No extra counselors found - all counselors in merged output exist in Master List")
    print("\nThe 30 'extra' counselors from the previous comparison are likely:")
    print("  - Name format variations (middle initials, etc.)")
    print("  - Counselors marked as LOA/resigned in Master List")
    print("  - They match when normalized but appear different")

print("\n" + "="*80)

