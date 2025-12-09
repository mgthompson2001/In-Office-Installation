#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify which LOA/Resigned counselors are in the merged file.
"""

import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

master_file = r"G:\Company\Master Counselor\Master Counselor List.xlsx"
merged_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Final Merged - Complete.xlsx"

# Expected LOA/Resigned from earlier analysis
expected_loa = [
    'Alam, Sumera F.', 'Armstrong, Uchenna', 'Basit, Amina', 'Ciervo, Nicole',
    'Daramola, Vanessa', 'Deschamps, Alexander', 'Haywood, Victoria', 'Jalim, Maria',
    'Lewis, Karim', 'Lilly-McFadden, Tammy', 'Lopez, Narda', 'Miller, Yasmin',
    'Muyir, Zeinab', 'Paolino, Valeriya', 'Peguero, Juana', 'Russell, Nordia',
    'Sadler, Shannon', 'Teague, Sonia', 'Vivelo, Mary', 'Weekes, Tunde',
    'Whitaker, Syeda', 'Zamor, Jennifer'
]

expected_resigned = [
    'Bam, Judith', 'Berkel, Trenice', 'Lazarus, Shira', 'Maldonado, Rhaida',
    'Naghi, Jessica', 'Risius, Locke', 'Van Dyke, Kendra', 'Walker, Tamara'
]

# Read merged file
merged_df = pd.read_excel(merged_file)
merged_counselors = set()

if 'Counselor Name' in merged_df.columns:
    for idx, row in merged_df.iterrows():
        name = str(row.get('Counselor Name', '')).strip()
        if name and name.lower() != 'nan':
            merged_counselors.add(name)

print("Checking which expected LOA/Resigned counselors are in merged file:")
print("="*80)

print("\nLOA Counselors:")
found_loa = []
missing_loa = []
for name in expected_loa:
    if name in merged_counselors:
        found_loa.append(name)
        print(f"  ✓ {name}")
    else:
        missing_loa.append(name)
        print(f"  ✗ {name} (NOT IN MERGED FILE)")

print(f"\nFound: {len(found_loa)}/{len(expected_loa)}")
print(f"Missing: {len(missing_loa)}/{len(expected_loa)}")

print("\nResigned Counselors:")
found_resigned = []
missing_resigned = []
for name in expected_resigned:
    if name in merged_counselors:
        found_resigned.append(name)
        print(f"  ✓ {name}")
    else:
        missing_resigned.append(name)
        print(f"  ✗ {name} (NOT IN MERGED FILE)")

print(f"\nFound: {len(found_resigned)}/{len(expected_resigned)}")
print(f"Missing: {len(missing_resigned)}/{len(expected_resigned)}")

print("\n" + "="*80)
print(f"Total LOA/Resigned in merged file: {len(found_loa) + len(found_resigned)}")
print("="*80)

