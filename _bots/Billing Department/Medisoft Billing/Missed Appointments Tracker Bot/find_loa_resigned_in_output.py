#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to find counselors in merged output who are LOA or Resigned in Master List.
These should NOT be in the output.
"""

import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# File paths
master_file = r"G:\Company\Master Counselor\Master Counselor List.xlsx"
merged_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Final Merged - Complete.xlsx"

print("="*80)
print("FINDING LOA/RESIGNED COUNSELORS IN OUTPUT")
print("="*80)

# Read Master Counselor List
print("\n1. Reading Master Counselor List...")
master_df = pd.read_excel(master_file)

# Build dictionary of counselor status
counselor_status = {}  # name -> {'status': 'active'|'loa'|'resigned', 'notes': ''}

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
        
        # Check status
        status = 'active'
        notes_text = ''
        
        if 'Notes' in master_df.columns:
            notes = str(row.get('Notes', '')).strip()
            notes_text = notes
            notes_lower = notes.lower()
            if 'loa' in notes_lower or 'leave of absence' in notes_lower:
                status = 'loa'
            elif 'resigned' in notes_lower or 'resign' in notes_lower:
                status = 'resigned'
        
        # Check all columns for status indicators
        for col in master_df.columns:
            cell_value = str(row.get(col, '')).lower()
            if 'loa' in cell_value or 'leave of absence' in cell_value:
                status = 'loa'
            if 'resigned' in cell_value or 'resign' in cell_value:
                status = 'resigned'
        
        counselor_status[counselor_name] = {
            'status': status,
            'notes': notes_text,
            'last_name': last_name,
            'first_name': first_name
        }

print(f"   [OK] Processed {len(counselor_status)} counselors from Master List")

# Count by status
active_count = sum(1 for v in counselor_status.values() if v['status'] == 'active')
loa_count = sum(1 for v in counselor_status.values() if v['status'] == 'loa')
resigned_count = sum(1 for v in counselor_status.values() if v['status'] == 'resigned')

print(f"   [OK] Active: {active_count}, LOA: {loa_count}, Resigned: {resigned_count}")

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

# Normalize function
def normalize_name(name):
    name = str(name).strip().lower()
    name = ' '.join(name.split())
    if ',' in name:
        parts = [p.strip() for p in name.split(',')]
        if len(parts) >= 2:
            return f"{parts[0]}, {parts[1]}"
    return name

# Find LOA/Resigned counselors in output
print("\n3. Finding LOA/Resigned counselors in merged output...")
loa_in_output = []
resigned_in_output = []

# Create normalized lookup
master_normalized = {}
for master_name, info in counselor_status.items():
    norm = normalize_name(master_name)
    if norm not in master_normalized:
        master_normalized[norm] = []
    master_normalized[norm].append((master_name, info))

for merged_name in merged_counselor_names:
    merged_norm = normalize_name(merged_name)
    
    if merged_norm in master_normalized:
        for master_name, info in master_normalized[merged_norm]:
            if info['status'] == 'loa':
                loa_in_output.append({
                    'merged_name': merged_name,
                    'master_name': master_name,
                    'status': 'LOA',
                    'notes': info['notes']
                })
                break
            elif info['status'] == 'resigned':
                resigned_in_output.append({
                    'merged_name': merged_name,
                    'master_name': master_name,
                    'status': 'Resigned',
                    'notes': info['notes']
                })
                break

# Print results
print("\n" + "="*80)
print("COUNSELORS IN OUTPUT WHO SHOULD NOT BE THERE")
print("="*80)

total_should_not_be_there = len(loa_in_output) + len(resigned_in_output)
print(f"\nTotal counselors that should NOT be in output: {total_should_not_be_there}")
print(f"  - LOA: {len(loa_in_output)}")
print(f"  - Resigned: {len(resigned_in_output)}")

if loa_in_output:
    print(f"\n{'='*80}")
    print("LOA COUNSELORS IN OUTPUT ({})".format(len(loa_in_output)))
    print("="*80)
    for i, item in enumerate(sorted(loa_in_output, key=lambda x: x['merged_name']), 1):
        # Count clients
        client_count = len(merged_df[merged_df['Counselor Name'].astype(str).str.strip() == item['merged_name']])
        print(f"\n{i:2d}. {item['merged_name']}")
        print(f"     - Master List name: {item['master_name']}")
        print(f"     - Status: {item['status']}")
        print(f"     - Client count in output: {client_count}")
        if item['notes']:
            print(f"     - Notes: {item['notes'][:100]}")

if resigned_in_output:
    print(f"\n{'='*80}")
    print("RESIGNED COUNSELORS IN OUTPUT ({})".format(len(resigned_in_output)))
    print("="*80)
    for i, item in enumerate(sorted(resigned_in_output, key=lambda x: x['merged_name']), 1):
        # Count clients
        client_count = len(merged_df[merged_df['Counselor Name'].astype(str).str.strip() == item['merged_name']])
        print(f"\n{i:2d}. {item['merged_name']}")
        print(f"     - Master List name: {item['master_name']}")
        print(f"     - Status: {item['status']}")
        print(f"     - Client count in output: {client_count}")
        if item['notes']:
            print(f"     - Notes: {item['notes'][:100]}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nThese {total_should_not_be_there} counselors are in the merged output but should NOT be")
print("because they are marked as LOA or Resigned in the Master Counselor List.")
print("\nThe bot should have filtered these out during processing.")
print("="*80)

