#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug name matching between Master List and merged file.
"""

import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

master_file = r"G:\Company\Master Counselor\Master Counselor List.xlsx"
merged_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Final Merged - Complete.xlsx"

def normalize_name(name):
    name = str(name).strip().lower()
    name = ' '.join(name.split())
    if ',' in name:
        parts = [p.strip() for p in name.split(',')]
        if len(parts) >= 2:
            return f"{parts[0]}, {parts[1]}"
    return name

# Read Master List
master_df = pd.read_excel(master_file)
loa_counselors = set()
resigned_counselors = set()

if 'Last Name' in master_df.columns and 'First Name' in master_df.columns:
    for idx, row in master_df.iterrows():
        last_name = str(row.get('Last Name', '')).strip() if pd.notna(row.get('Last Name')) else ""
        first_name = str(row.get('First Name', '')).strip() if pd.notna(row.get('First Name')) else ""
        
        if not last_name or not first_name or last_name.lower() == 'nan' or first_name.lower() == 'nan':
            continue
        
        if any(keyword in last_name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
            continue
        
        counselor_name = f"{last_name}, {first_name}"
        notes_text = str(row.get('Notes', '')).strip() if pd.notna(row.get('Notes')) else ""
        notes_lower = notes_text.lower() if notes_text else ""
        
        is_loa = False
        if notes_lower:
            loa_keywords = ['loa', 'leave of absence', 'on leave']
            if any(keyword in notes_lower for keyword in loa_keywords):
                if 'returned from' not in notes_lower and 'has returned' not in notes_lower and 'returning from' not in notes_lower:
                    is_loa = True
        
        is_resigned = False
        if notes_lower:
            resigned_keywords = ['resigned', 'resigning', 'resignation', 'will be resigning']
            if any(keyword in notes_lower for keyword in resigned_keywords):
                if 'rescinded' not in notes_lower:
                    is_resigned = True
        
        if is_loa:
            loa_counselors.add(counselor_name)
        if is_resigned:
            resigned_counselors.add(counselor_name)

# Read merged file
merged_df = pd.read_excel(merged_file)
merged_counselors = set()

if 'Counselor Name' in merged_df.columns:
    for idx, row in merged_df.iterrows():
        name = str(row.get('Counselor Name', '')).strip()
        if name and name.lower() != 'nan':
            merged_counselors.add(name)

print("LOA Counselors from Master List:")
print("="*80)
loa_normalized = {normalize_name(name): name for name in loa_counselors}
merged_normalized = {normalize_name(name): name for name in merged_counselors}

found_loa = []
missing_loa = []
for norm, orig in loa_normalized.items():
    if norm in merged_normalized:
        found_loa.append((orig, merged_normalized[norm]))
        print(f"  ✓ {orig} -> {merged_normalized[norm]}")
    else:
        missing_loa.append(orig)
        print(f"  ✗ {orig} (NOT FOUND in merged file)")

print(f"\nFound: {len(found_loa)}/{len(loa_counselors)}")
print(f"Missing: {len(missing_loa)}/{len(loa_counselors)}")

print("\nResigned Counselors from Master List:")
print("="*80)
resigned_normalized = {normalize_name(name): name for name in resigned_counselors}

found_resigned = []
missing_resigned = []
for norm, orig in resigned_normalized.items():
    if norm in merged_normalized:
        found_resigned.append((orig, merged_normalized[norm]))
        print(f"  ✓ {orig} -> {merged_normalized[norm]}")
    else:
        missing_resigned.append(orig)
        print(f"  ✗ {orig} (NOT FOUND in merged file)")

print(f"\nFound: {len(found_resigned)}/{len(resigned_counselors)}")
print(f"Missing: {len(missing_resigned)}/{len(resigned_counselors)}")

print("\n" + "="*80)
print(f"Total LOA/Resigned in merged file: {len(found_loa) + len(found_resigned)}")
print("="*80)

