#!/usr/bin/env python3
"""Deep check of procedure code extraction"""
import pdfplumber
import re
import pandas as pd

output_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\July Medicare Medisoft Project\Medisoft Penelope synthesis excel output\scrape.xlsx"
pdf_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\Transaction List 7.1.25-8.1.25.pdf"

# Get sample rows with blank procedure codes
df = pd.read_excel(output_path)
matched_blank = df[(df['Match_Status'] == 'Matched') & (df['Procedure Code'].isna() | (df['Procedure Code'] == ''))]

print("="*80)
print("CHECKING PDF FOR ROWS WITH MISSING PROCEDURE CODES")
print("="*80)

# Get sample PT codes to search
sample_pt_codes = matched_blank['Chart_Value'].dropna().unique()[:10]
print(f"\nSearching for {len(sample_pt_codes)} sample PT codes in PDF...")

found_examples = []

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        if tables:
            for table in tables:
                if table and len(table) > 1:
                    for row in table[1:]:
                        if not row:
                            continue
                        
                        # Get PT Code
                        pt_code = ""
                        if 4 < len(row) and row[4]:
                            pt_val = str(row[4]).strip().upper()
                            if re.match(r'^[A-Z]{2,7}\d{3,}$', pt_val):
                                pt_code = pt_val
                        
                        # Check if this is one of our sample PT codes
                        if pt_code in [str(s).strip().upper() for s in sample_pt_codes]:
                            # Extract all potential procedure codes
                            date = ""
                            procedure_codes_found = {}
                            
                            # Column 1: Date
                            if 1 < len(row) and row[1]:
                                date_val = str(row[1]).strip()
                                if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', date_val):
                                    date = date_val
                            
                            # Check all columns for 5-digit numbers (procedure codes)
                            for col_idx in range(len(row)):
                                if col_idx < len(row) and row[col_idx]:
                                    val = str(row[col_idx]).strip()
                                    # Check if it's a 5-digit number
                                    if val.isdigit() and len(val) == 5:
                                        procedure_codes_found[col_idx] = val
                            
                            # Also check for case numbers (5-digit numbers in Column 6)
                            case_num = ""
                            if 6 < len(row) and row[6]:
                                case_val = str(row[6]).strip()
                                if case_val.isdigit() and len(case_val) == 5:
                                    case_num = case_val
                            
                            found_examples.append({
                                'page': page_num,
                                'pt_code': pt_code,
                                'date': date,
                                'case_num': case_num,
                                'procedure_codes': procedure_codes_found,
                                'row_preview': [str(cell)[:10] if cell else "" for cell in row[:15]]
                            })
                            
                            if len(found_examples) >= 20:
                                break
                
                if len(found_examples) >= 20:
                    break
        
        if len(found_examples) >= 20:
            break

if found_examples:
    print(f"\nFound {len(found_examples)} examples:")
    for i, ex in enumerate(found_examples[:10], 1):
        print(f"\n  Example {i} (Page {ex['page']}):")
        print(f"    PT Code: {ex['pt_code']}")
        print(f"    Date: {ex['date']}")
        print(f"    Case Number (Col 6): {ex['case_num']}")
        print(f"    5-digit numbers found: {ex['procedure_codes']}")
        if not ex['procedure_codes']:
            print(f"    ⚠️  NO PROCEDURE CODE FOUND!")
        print(f"    First 15 columns: {ex['row_preview']}")
        
        # Determine which should be procedure code
        if 10 in ex['procedure_codes']:
            print(f"    ✓ Procedure code in Column 10: {ex['procedure_codes'][10]}")
        elif 11 in ex['procedure_codes']:
            print(f"    ✓ Procedure code in Column 11: {ex['procedure_codes'][11]}")
        elif 7 in ex['procedure_codes']:
            print(f"    ⚠️  Procedure code might be in Column 7: {ex['procedure_codes'][7]}")
        else:
            print(f"    ❌ No procedure code in columns 10 or 11!")

# Check procedure code positions more systematically
print("\n" + "="*80)
print("STATISTICAL ANALYSIS OF PROCEDURE CODE POSITIONS")
print("="*80)

procedure_by_position = {}  # position: count
rows_with_no_procedure = 0
rows_with_procedure = 0

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages[:30], 1):  # Check first 30 pages
        tables = page.extract_tables()
        if tables:
            for table in tables:
                if table and len(table) > 1:
                    for row in table[1:]:
                        if not row:
                            continue
                        
                        # Get PT Code to verify it's a data row
                        pt_code = ""
                        if 4 < len(row) and row[4]:
                            pt_val = str(row[4]).strip().upper()
                            if re.match(r'^[A-Z]{2,7}\d{3,}$', pt_val):
                                pt_code = pt_val
                        
                        if pt_code:  # Only count rows with PT codes
                            # Check columns 7, 10, 11 for 5-digit codes
                            found_procedure = False
                            
                            for col_idx in [7, 10, 11]:
                                if col_idx < len(row) and row[col_idx]:
                                    val = str(row[col_idx]).strip()
                                    if val.isdigit() and len(val) == 5:
                                        if col_idx not in procedure_by_position:
                                            procedure_by_position[col_idx] = 0
                                        procedure_by_position[col_idx] += 1
                                        found_procedure = True
                                        break  # Count first match only
                            
                            if found_procedure:
                                rows_with_procedure += 1
                            else:
                                rows_with_no_procedure += 1

print(f"\nRows with procedure codes (first 30 pages): {rows_with_procedure}")
print(f"Rows without procedure codes (first 30 pages): {rows_with_no_procedure}")
print(f"\nProcedure code positions (first 30 pages):")
for col_idx, count in sorted(procedure_by_position.items(), key=lambda x: x[1], reverse=True):
    print(f"  Column {col_idx}: {count} occurrences")

