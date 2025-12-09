#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to compare input and output Excel files for remainder run.
"""

import pandas as pd
import os
import sys

# Output Excel file
output_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Log for remaining Run\Final Missing\remainder.xlsx"

# Input Excel file (provided by user)
input_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Missing Active Counselors - For Re-Analysis.xlsx"

if not os.path.exists(input_file):
    print(f"ERROR: Input file not found: {input_file}")
    sys.exit(1)

print("="*80)
print("COMPARING INPUT vs OUTPUT")
print("="*80)
print(f"\nInput file: {os.path.basename(input_file)}")
print(f"Output file: {os.path.basename(output_file)}")
print("\n" + "="*80)

# Read input Excel
print("\nReading input Excel...")
input_df = pd.read_excel(input_file)
print(f"Input has {len(input_df)} rows")

# Extract counselor names from input
input_counselor_names = set()
if 'Last Name' in input_df.columns and 'First Name' in input_df.columns:
    for idx, row in input_df.iterrows():
        last_name = str(row.get('Last Name', '')).strip()
        first_name = str(row.get('First Name', '')).strip()
        if last_name and first_name and last_name.lower() != 'nan' and first_name.lower() != 'nan':
            # Skip KEY rows
            if any(keyword in last_name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
                continue
            if any(keyword in first_name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
                continue
            counselor_name = f"{last_name}, {first_name}"
            input_counselor_names.add(counselor_name)
elif 'Counselor Name' in input_df.columns:
    for idx, row in input_df.iterrows():
        name = str(row.get('Counselor Name', '')).strip()
        if name and name.lower() != 'nan':
            if any(keyword in name.lower() for keyword in ['key', 'all counselors', 'minimum', 'cases']):
                continue
            input_counselor_names.add(name)

print(f"Found {len(input_counselor_names)} unique counselors in INPUT")

# Read output Excel
print("\nReading output Excel...")
output_df = pd.read_excel(output_file)
print(f"Output has {len(output_df)} rows")

# Extract counselor names from output
output_counselor_names = set()
if 'Counselor Name' in output_df.columns:
    for idx, row in output_df.iterrows():
        name = str(row.get('Counselor Name', '')).strip()
        if name and name.lower() != 'nan':
            output_counselor_names.add(name)

print(f"Found {len(output_counselor_names)} unique counselors in OUTPUT")

# Normalize names for comparison
def normalize_name(name):
    name = str(name).strip().lower()
    name = ' '.join(name.split())
    if ',' in name:
        parts = [p.strip() for p in name.split(',')]
        if len(parts) >= 2:
            return f"{parts[0]}, {parts[1]}"
    return name

input_normalized = {normalize_name(name): name for name in input_counselor_names}
output_normalized = {normalize_name(name): name for name in output_counselor_names}

# Find missing
missing_counselors = []
for norm_name, orig_name in input_normalized.items():
    if norm_name not in output_normalized:
        missing_counselors.append(orig_name)

# Find extra
extra_counselors = []
for norm_name, orig_name in output_normalized.items():
    if norm_name not in input_normalized:
        extra_counselors.append(orig_name)

# Print results
print("\n" + "="*80)
print("RESULTS")
print("="*80)
print(f"\nExpected (from input): {len(input_counselor_names)} counselors")
print(f"Found (in output): {len(output_counselor_names)} counselors")
print(f"Missing: {len(missing_counselors)} counselors")
print(f"Extra (not in input): {len(extra_counselors)} counselors")

if missing_counselors:
    print(f"\nMISSING COUNSELORS ({len(missing_counselors)}):")
    for i, name in enumerate(missing_counselors, 1):
        print(f"  {i}. {name}")
else:
    print("\nSUCCESS: All counselors from input were found in output!")

if extra_counselors:
    print(f"\nEXTRA COUNSELORS in output ({len(extra_counselors)}):")
    for i, name in enumerate(extra_counselors[:10], 1):
        print(f"  {i}. {name}")
    if len(extra_counselors) > 10:
        print(f"  ... and {len(extra_counselors) - 10} more")

# Match rate
if len(input_counselor_names) > 0:
    match_rate = ((len(input_counselor_names) - len(missing_counselors)) / len(input_counselor_names)) * 100
    print(f"\nMatch Rate: {match_rate:.1f}% ({len(input_counselor_names) - len(missing_counselors)}/{len(input_counselor_names)})")

print("\n" + "="*80)

