#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive comparison between Master Counselor List and merged output file.
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

print("="*80)
print("COMPREHENSIVE COMPARISON: MASTER LIST vs MERGED FILE")
print("="*80)

# Read Master Counselor List
print("\n1. Reading Master Counselor List...")
master_df = pd.read_excel(master_file)

master_all_counselors = set()
master_active_counselors = set()
master_loa_counselors = set()
master_resigned_counselors = set()
master_terminated_counselors = set()

if 'Last Name' in master_df.columns and 'First Name' in master_df.columns:
    for idx, row in master_df.iterrows():
        last_name = str(row.get('Last Name', '')).strip() if pd.notna(row.get('Last Name')) else ""
        first_name = str(row.get('First Name', '')).strip() if pd.notna(row.get('First Name')) else ""
        
        if not last_name or not first_name or last_name.lower() == 'nan' or first_name.lower() == 'nan':
            continue
        
        # Skip KEY rows
        if any(keyword in last_name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
            continue
        if any(keyword in first_name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
            continue
        
        counselor_name = f"{last_name}, {first_name}"
        master_all_counselors.add(counselor_name)
        
        # Check Notes
        notes_text = str(row.get('Notes', '')).strip() if pd.notna(row.get('Notes')) else ""
        notes_lower = notes_text.lower() if notes_text else ""
        
        # Check termination date
        date_of_term_value = row.get('Date of Term')
        is_terminated = False
        if pd.notna(date_of_term_value):
            date_str = str(date_of_term_value).strip().lower()
            non_date_values = ['antia', 'n/a', 'na', 'none', '', ' ', '-', '--']
            if date_str not in non_date_values:
                has_digits = any(char.isdigit() for char in date_str)
                has_date_separators = '/' in date_str or '-' in date_str
                if has_digits and (has_date_separators or len(date_str) >= 6):
                    is_terminated = True
        
        # Check LOA
        is_loa = False
        if notes_lower:
            loa_keywords = ['loa', 'leave of absence', 'on leave']
            if any(keyword in notes_lower for keyword in loa_keywords):
                if 'returned from' not in notes_lower and 'has returned' not in notes_lower and 'returning from' not in notes_lower:
                    is_loa = True
        
        # Check Resigned
        is_resigned = False
        if notes_lower:
            resigned_keywords = ['resigned', 'resigning', 'resignation', 'will be resigning']
            if any(keyword in notes_lower for keyword in resigned_keywords):
                if 'rescinded' not in notes_lower:
                    is_resigned = True
        
        # Categorize
        if is_terminated:
            master_terminated_counselors.add(counselor_name)
        elif is_loa:
            master_loa_counselors.add(counselor_name)
        elif is_resigned:
            master_resigned_counselors.add(counselor_name)
        else:
            master_active_counselors.add(counselor_name)

print(f"   [OK] Total counselors in Master List: {len(master_all_counselors)}")
print(f"   [OK] Active counselors: {len(master_active_counselors)}")
print(f"   [OK] LOA counselors: {len(master_loa_counselors)}")
print(f"   [OK] Resigned counselors: {len(master_resigned_counselors)}")
print(f"   [OK] Terminated counselors: {len(master_terminated_counselors)}")

# Read merged file
print("\n2. Reading merged output file...")
merged_df = pd.read_excel(merged_file)
merged_counselors = set()

if 'Counselor Name' in merged_df.columns:
    for idx, row in merged_df.iterrows():
        name = str(row.get('Counselor Name', '')).strip()
        if name and name.lower() != 'nan':
            merged_counselors.add(name)

print(f"   [OK] Total counselors in merged file: {len(merged_counselors)}")

# Normalize names for comparison
master_all_normalized = {normalize_name(name): name for name in master_all_counselors}
master_active_normalized = {normalize_name(name): name for name in master_active_counselors}
merged_normalized = {normalize_name(name): name for name in merged_counselors}

# Find missing (in Master but not in merged)
print("\n3. Finding counselors in Master List but NOT in merged file...")
missing_from_merged = []
for norm, orig in master_active_normalized.items():
    if norm not in merged_normalized:
        missing_from_merged.append(orig)

print(f"   [OK] Missing active counselors: {len(missing_from_merged)}")

# Find extra (in merged but not in Master)
print("\n4. Finding counselors in merged file but NOT in Master List...")
extra_in_merged = []
for norm, orig in merged_normalized.items():
    if norm not in master_all_normalized:
        extra_in_merged.append(orig)

print(f"   [OK] Extra counselors in merged: {len(extra_in_merged)}")

# Find LOA/Resigned in merged
print("\n5. Finding LOA/Resigned counselors in merged file...")
loa_in_merged = []
resigned_in_merged = []
master_loa_normalized = {normalize_name(name): name for name in master_loa_counselors}
master_resigned_normalized = {normalize_name(name): name for name in master_resigned_counselors}

for norm, orig in merged_normalized.items():
    if norm in master_loa_normalized:
        loa_in_merged.append(orig)
    elif norm in master_resigned_normalized:
        resigned_in_merged.append(orig)

print(f"   [OK] LOA counselors in merged: {len(loa_in_merged)}")
print(f"   [OK] Resigned counselors in merged: {len(resigned_in_merged)}")

# Print detailed results
print("\n" + "="*80)
print("DETAILED RESULTS")
print("="*80)

print(f"\n📊 SUMMARY:")
print(f"   • Total counselors in Master List: {len(master_all_counselors)}")
print(f"   • Active counselors in Master List: {len(master_active_counselors)}")
print(f"   • Total counselors in merged file: {len(merged_counselors)}")
print(f"   • LOA counselors in merged: {len(loa_in_merged)}")
print(f"   • Resigned counselors in merged: {len(resigned_in_merged)}")
print(f"   • Missing active counselors: {len(missing_from_merged)}")
print(f"   • Extra counselors (not in Master): {len(extra_in_merged)}")

if missing_from_merged:
    print(f"\n❌ MISSING ACTIVE COUNSELORS ({len(missing_from_merged)}) - In Master but NOT in merged:")
    for i, name in enumerate(sorted(missing_from_merged), 1):
        print(f"   {i:2d}. {name}")

if extra_in_merged:
    print(f"\n⚠️  EXTRA COUNSELORS ({len(extra_in_merged)}) - In merged but NOT in Master List:")
    for i, name in enumerate(sorted(extra_in_merged), 1):
        print(f"   {i:2d}. {name}")

if loa_in_merged:
    print(f"\n📋 LOA COUNSELORS IN MERGED ({len(loa_in_merged)}):")
    for i, name in enumerate(sorted(loa_in_merged), 1):
        print(f"   {i:2d}. {name}")

if resigned_in_merged:
    print(f"\n📋 RESIGNED COUNSELORS IN MERGED ({len(resigned_in_merged)}):")
    for i, name in enumerate(sorted(resigned_in_merged), 1):
        print(f"   {i:2d}. {name}")

# Calculate match rate
if len(master_active_counselors) > 0:
    found_count = len(master_active_counselors) - len(missing_from_merged)
    match_rate = (found_count / len(master_active_counselors)) * 100
    print(f"\n📈 MATCH RATE:")
    print(f"   • Found: {found_count}/{len(master_active_counselors)} active counselors ({match_rate:.1f}%)")
    print(f"   • Missing: {len(missing_from_merged)} active counselors")

print("\n" + "="*80)

