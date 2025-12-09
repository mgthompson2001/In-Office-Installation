#!/usr/bin/env python3
"""Check column positions in output Excel"""
import pandas as pd

output_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\July Medicare Medisoft Project\Medisoft Penelope synthesis excel output\scrape.xlsx"

df = pd.read_excel(output_path)

print("="*80)
print("CURRENT COLUMN ORDER")
print("="*80)

# Convert column index to Excel column letters
def num_to_col(num):
    result = ""
    num += 1  # Convert 0-based to 1-based
    while num > 0:
        num -= 1
        result = chr(65 + (num % 26)) + result
        num //= 26
    return result

print("\nAll columns with Excel column letters:")
for i, col in enumerate(df.columns):
    excel_col = num_to_col(i)
    print(f"  {excel_col:3s} ({i:2d}): {col}")

print("\n\nColumns R-V (17-21):")
for i in range(17, min(22, len(df.columns))):
    excel_col = num_to_col(i)
    print(f"  {excel_col} ({i}): {df.columns[i]}")

print("\n\nExcel First Name and Last Name positions:")
if 'Excel_First_Name' in df.columns:
    idx = df.columns.get_loc('Excel_First_Name')
    print(f"  Excel_First_Name: Column {num_to_col(idx)} ({idx})")
if 'Excel_Last_Name' in df.columns:
    idx = df.columns.get_loc('Excel_Last_Name')
    print(f"  Excel_Last_Name: Column {num_to_col(idx)} ({idx})")

print("\n\nFirst few columns (A-E):")
for i in range(min(5, len(df.columns))):
    excel_col = num_to_col(i)
    print(f"  {excel_col} ({i}): {df.columns[i]}")

