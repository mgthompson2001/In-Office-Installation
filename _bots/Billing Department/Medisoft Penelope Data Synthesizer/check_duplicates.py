#!/usr/bin/env python3
"""Check for duplicate columns in output Excel"""
import pandas as pd

output_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\July Medicare Medisoft Project\Medisoft Penelope synthesis excel output\scrape.xlsx"

df = pd.read_excel(output_path)

print("="*80)
print("OUTPUT EXCEL COLUMN ANALYSIS")
print("="*80)
print(f"\nTotal columns: {len(df.columns)}")
print(f"Total rows: {len(df)}")

print(f"\nColumn names:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:3d}. {col}")

# Check for duplicate data within rows
print(f"\n{'='*80}")
print("CHECKING FOR DUPLICATE DATA")
print(f"{'='*80}")

# Sample a few rows to see what's duplicated
print("\nFirst row sample:")
first_row = df.iloc[0]
for col in df.columns:
    val = first_row[col]
    if pd.notna(val) and val != '':
        print(f"  {col}: {val}")

print("\n\nChecking for columns with same data...")
# Find columns that have identical values across rows
duplicate_groups = []
checked_cols = set()

for col1 in df.columns:
    if col1 in checked_cols:
        continue
    group = [col1]
    for col2 in df.columns:
        if col1 != col2 and col2 not in checked_cols:
            # Check if columns are identical
            if df[col1].equals(df[col2]):
                group.append(col2)
                checked_cols.add(col2)
    
    if len(group) > 1:
        duplicate_groups.append(group)
    checked_cols.add(col1)

if duplicate_groups:
    print(f"\nFound {len(duplicate_groups)} groups of identical columns:")
    for i, group in enumerate(duplicate_groups, 1):
        print(f"\n  Group {i} ({len(group)} columns):")
        for col in group:
            print(f"    - {col}")
        # Show sample value
        print(f"    Sample value: {df[group[0]].iloc[0] if len(df) > 0 else 'N/A'}")

# Check for similar column names that might contain duplicate data
print(f"\n{'='*80}")
print("CHECKING FOR RELATED COLUMNS (potential duplicates)")
print(f"{'='*80}")

# Look for columns with similar names
similar_cols = {}
for col in df.columns:
    base_name = col.replace('PDF_', '').replace('Excel_', '').replace('_', '').lower()
    if base_name not in similar_cols:
        similar_cols[base_name] = []
    similar_cols[base_name].append(col)

# Show groups with multiple columns
for base, cols in similar_cols.items():
    if len(cols) > 1:
        print(f"\n  '{base}' variants ({len(cols)} columns):")
        for col in cols:
            non_null = df[col].notna().sum()
            print(f"    - {col} ({non_null} non-null values)")
            # Check if they're the same
            if len(cols) == 2:
                col1, col2 = cols
                if df[col1].equals(df[col2]):
                    print(f"      ⚠️  Identical to {cols[1 if cols.index(col) == 0 else 0]}")

# Show sample row with all PDF_ prefixed columns
pdf_cols = [col for col in df.columns if col.startswith('PDF_')]
print(f"\n{'='*80}")
print(f"PDF_ COLUMNS ({len(pdf_cols)} total)")
print(f"{'='*80}")
for col in sorted(pdf_cols):
    non_null = df[col].notna().sum()
    if non_null > 0:
        print(f"  {col}: {non_null} non-null values")

# Show sample row with all Excel_ prefixed columns
excel_cols = [col for col in df.columns if col.startswith('Excel_')]
print(f"\n{'='*80}")
print(f"Excel_ COLUMNS ({len(excel_cols)} total)")
print(f"{'='*80}")
for col in sorted(excel_cols):
    non_null = df[col].notna().sum()
    if non_null > 0:
        print(f"  {col}: {non_null} non-null values")

