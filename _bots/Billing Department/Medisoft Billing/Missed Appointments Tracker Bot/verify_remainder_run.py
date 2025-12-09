#!/usr/bin/env python3
"""
Script to verify if the bot processed all counselors from the input Excel file.
"""

import pandas as pd
import os
from pathlib import Path

# Output Excel file
output_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Log for remaining Run\Final Missing\remainder.xlsx"

# Try to find the input Excel file (the one with missing active counselors)
input_file_candidates = [
    r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Log for remaining Run\missing_active_counselors_for_reanalysis.xlsx",
    r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\_bots\Billing Department\Medisoft Billing\Missed Appointments Tracker Bot\missing_active_counselors_for_reanalysis.xlsx",
]

# Find the input file
input_file = None
for candidate in input_file_candidates:
    if os.path.exists(candidate):
        input_file = candidate
        break

if not input_file:
    print("ERROR: Could not find the input Excel file with missing active counselors.")
    print("Please provide the path to the input Excel file that was used for this run.")
    exit(1)

print(f"Input file: {input_file}")
print(f"Output file: {output_file}")
print("\n" + "="*80 + "\n")

# Read input Excel (the list of counselors that should have been processed)
print("Reading input Excel file...")
input_df = pd.read_excel(input_file)
print(f"Input Excel has {len(input_df)} rows")

# Get counselor names from input (assuming standard Master Counselor List format)
# Try to find the name columns
input_counselor_names = set()
if 'Last Name' in input_df.columns and 'First Name' in input_df.columns:
    # Combine Last Name and First Name
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

print(f"Found {len(input_counselor_names)} unique counselors in input file")
print(f"Sample counselors from input: {list(input_counselor_names)[:5]}")

# Read output Excel
print("\nReading output Excel file...")
output_df = pd.read_excel(output_file)
print(f"Output Excel has {len(output_df)} rows")

# Get counselor names from output
output_counselor_names = set()
if 'Counselor Name' in output_df.columns:
    for idx, row in output_df.iterrows():
        name = str(row.get('Counselor Name', '')).strip()
        if name and name.lower() != 'nan':
            output_counselor_names.add(name)
elif 'Client Name' in output_df.columns:
    # Sometimes counselor names might be in a different format
    print("Warning: 'Counselor Name' column not found, checking other columns...")

print(f"Found {len(output_counselor_names)} unique counselors in output file")
print(f"Sample counselors from output: {list(output_counselor_names)[:5]}")

# Normalize names for comparison (handle different formats)
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
input_normalized = {normalize_name(name): name for name in input_counselor_names}
output_normalized = {normalize_name(name): name for name in output_counselor_names}

# Find missing counselors
missing_counselors = []
for norm_name, orig_name in input_normalized.items():
    if norm_name not in output_normalized:
        missing_counselors.append(orig_name)

# Find extra counselors (in output but not in input)
extra_counselors = []
for norm_name, orig_name in output_normalized.items():
    if norm_name not in input_normalized:
        extra_counselors.append(orig_name)

# Print results
print("\n" + "="*80)
print("VERIFICATION RESULTS")
print("="*80)
print(f"\nInput counselors (expected): {len(input_counselor_names)}")
print(f"Output counselors (found): {len(output_counselor_names)}")
print(f"Missing counselors: {len(missing_counselors)}")
print(f"Extra counselors (not in input): {len(extra_counselors)}")

if missing_counselors:
    print(f"\n❌ MISSING COUNSELORS ({len(missing_counselors)}):")
    for i, name in enumerate(missing_counselors, 1):
        print(f"  {i}. {name}")
else:
    print("\n✅ SUCCESS: All counselors from input file were found in output!")

if extra_counselors:
    print(f"\n⚠️  EXTRA COUNSELORS in output (not in input) ({len(extra_counselors)}):")
    for i, name in enumerate(extra_counselors[:10], 1):  # Show first 10
        print(f"  {i}. {name}")
    if len(extra_counselors) > 10:
        print(f"  ... and {len(extra_counselors) - 10} more")

# Calculate match rate
if len(input_counselor_names) > 0:
    match_rate = ((len(input_counselor_names) - len(missing_counselors)) / len(input_counselor_names)) * 100
    print(f"\n📊 Match Rate: {match_rate:.1f}% ({len(input_counselor_names) - len(missing_counselors)}/{len(input_counselor_names)})")

print("\n" + "="*80)

