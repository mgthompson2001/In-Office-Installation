#!/usr/bin/env python3
"""Check the output Excel file and compare with PDF"""
import pandas as pd
import pdfplumber
import re

output_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\July Medicare Medisoft Project\Medisoft Penelope synthesis excel output\scrape.xlsx"
pdf_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\Transaction List 7.1.25-8.1.25.pdf"

# Read output Excel
print("="*80)
print("OUTPUT EXCEL ANALYSIS")
print("="*80)
df = pd.read_excel(output_path)

print(f"\nTotal rows: {len(df)}")
print(f"Rows with modifiers (not empty): {df['Modifier'].notna().sum()}")
print(f"Rows with non-empty modifiers: {(df['Modifier'] != '').sum()}")
print(f"Rows with empty modifiers: {(df['Modifier'] == '').sum()}")

# Check for modifier column variations
modifier_cols = [col for col in df.columns if 'modif' in col.lower() or col.lower() == 'mod']
print(f"\nModifier-related columns: {modifier_cols}")

if 'Modifier' in df.columns:
    print(f"\nModifier value distribution (top 20):")
    print(df['Modifier'].value_counts().head(20))
    
    print(f"\nFirst 15 rows showing modifier data:")
    display_cols = ['Chart_Value', 'Modifier', 'Date_of_Service', 'PDF_Col_14_Provider', 'PDF_Col_10_Procedure', 'Match_Status']
    available_cols = [col for col in display_cols if col in df.columns]
    print(df[available_cols].head(15).to_string())

# Now check PDF directly
print("\n" + "="*80)
print("PDF DIRECT ANALYSIS")
print("="*80)

pdf_modifiers = []
pdf_rows_with_modifiers = 0
pdf_total_rows = 0

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages[:5], 1):  # Check first 5 pages
        tables = page.extract_tables()
        if tables:
            for table in tables:
                if table and len(table) > 1:
                    for row_idx, row in enumerate(table[1:], 1):
                        pdf_total_rows += 1
                        if row and len(row) > 12:
                            modifier = str(row[12]).strip() if 12 < len(row) and row[12] else ''
                            pt_code = str(row[4]).strip() if 4 < len(row) and row[4] else ''
                            date = str(row[1]).strip() if 1 < len(row) and row[1] else ''
                            
                            # Validate modifier (should be 1-2 digits or alphanumeric)
                            if modifier and re.match(r'^[0-9]{1,2}$|^[A-Z][0-9]$', modifier.upper()) and len(modifier) <= 3:
                                pdf_modifiers.append((pt_code, date, modifier))
                                pdf_rows_with_modifiers += 1
                                
                                if len(pdf_modifiers) <= 30:  # Show first 30
                                    print(f"PDF Row: PT={pt_code}, Date={date}, Modifier={modifier}")

print(f"\nPDF Summary (first 5 pages):")
print(f"  Total PDF rows checked: {pdf_total_rows}")
print(f"  PDF rows with valid modifiers: {pdf_rows_with_modifiers}")
print(f"  Modifier coverage: {pdf_rows_with_modifiers/pdf_total_rows*100:.1f}%")

# Compare
print("\n" + "="*80)
print("COMPARISON")
print("="*80)
excel_modifiers = (df['Modifier'] != '').sum()
print(f"Excel rows with modifiers: {excel_modifiers} / {len(df)} ({excel_modifiers/len(df)*100:.1f}%)")
print(f"PDF rows with modifiers (first 5 pages): {pdf_rows_with_modifiers} / {pdf_total_rows} ({pdf_rows_with_modifiers/pdf_total_rows*100:.1f}%)")

