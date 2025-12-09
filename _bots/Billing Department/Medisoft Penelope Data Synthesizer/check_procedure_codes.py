#!/usr/bin/env python3
"""Check for missing procedure codes in matched rows"""
import pandas as pd
import pdfplumber
import re

output_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\July Medicare Medisoft Project\Medisoft Penelope synthesis excel output\scrape.xlsx"
pdf_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\Transaction List 7.1.25-8.1.25.pdf"

# Read Excel
df = pd.read_excel(output_path)

print("="*80)
print("PROCEDURE CODE ANALYSIS")
print("="*80)

# Check matched rows with blank procedure codes
matched_rows = df[df['Match_Status'] == 'Matched']
blank_procedure_matched = matched_rows[matched_rows['Procedure Code'].isna() | (matched_rows['Procedure Code'] == '')]

print(f"\nTotal matched rows: {len(matched_rows)}")
print(f"Matched rows with blank procedure codes: {len(blank_procedure_matched)}")
print(f"Matched rows with procedure codes: {len(matched_rows) - len(blank_procedure_matched)}")

if len(blank_procedure_matched) > 0:
    print(f"\nSample of matched rows with blank procedure codes (first 10):")
    display_cols = ['Match_Status', 'Chart_Value', 'PT_Code', 'Date_of_Service', 'Procedure Code', 'Modifier', 'PDF_Col_10', 'PDF_Col_11']
    available_cols = [col for col in display_cols if col in blank_procedure_matched.columns]
    print(blank_procedure_matched[available_cols].head(10).to_string())
    
    # Get sample Chart_Value and Date_of_Service to check in PDF
    sample_charts = blank_procedure_matched['Chart_Value'].dropna().unique()[:5]
    sample_dates = blank_procedure_matched['Date_of_Service'].dropna().unique()[:5]
    
    print(f"\nSample Chart values to check in PDF: {list(sample_charts)}")
    print(f"Sample Dates to check in PDF: {list(sample_dates)}")

# Now check PDF for these specific rows
print("\n" + "="*80)
print("CHECKING PDF FOR SAMPLE ROWS")
print("="*80)

# Check first few pages for rows matching the sample charts/dates
if len(blank_procedure_matched) > 0:
    sample_chart = blank_procedure_matched.iloc[0]['Chart_Value'] if pd.notna(blank_procedure_matched.iloc[0]['Chart_Value']) else None
    sample_date = blank_procedure_matched.iloc[0]['Date_of_Service'] if pd.notna(blank_procedure_matched.iloc[0]['Date_of_Service']) else None
    
    if sample_chart:
        print(f"\nLooking for Chart '{sample_chart}' in PDF...")
        
        found_rows = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages[:20], 1):  # Check first 20 pages
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        if table and len(table) > 1:
                            for row_idx, row in enumerate(table[1:], 1):
                                if not row:
                                    continue
                                
                                # Check Column 4 for PT Code
                                pt_code = ""
                                if 4 < len(row) and row[4]:
                                    pt_val = str(row[4]).strip().upper()
                                    if re.match(r'^[A-Z]{2,7}\d{3,}$', pt_val):
                                        pt_code = pt_val
                                
                                # Check if this matches our sample
                                if pt_code == str(sample_chart).strip().upper():
                                    # Extract procedure code
                                    procedure = ""
                                    date = ""
                                    
                                    # Column 1: Date
                                    if 1 < len(row) and row[1]:
                                        date_val = str(row[1]).strip()
                                        if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', date_val):
                                            date = date_val
                                    
                                    # Column 10: Procedure Code
                                    if 10 < len(row) and row[10]:
                                        proc_val = str(row[10]).strip()
                                        if proc_val.isdigit() and len(proc_val) == 5:
                                            procedure = proc_val
                                    
                                    # Column 11: Procedure Code (backup)
                                    if not procedure and 11 < len(row) and row[11]:
                                        proc_val = str(row[11]).strip()
                                        if proc_val.isdigit() and len(proc_val) == 5:
                                            procedure = proc_val
                                    
                                    found_rows.append({
                                        'page': page_num,
                                        'pt_code': pt_code,
                                        'date': date,
                                        'procedure_col10': str(row[10]).strip() if 10 < len(row) and row[10] else "EMPTY",
                                        'procedure_col11': str(row[11]).strip() if 11 < len(row) and row[11] else "EMPTY",
                                        'procedure_found': procedure,
                                        'full_row': [str(cell)[:15] if cell else "" for cell in row[:15]]
                                    })
                                    
                                    if len(found_rows) >= 5:
                                        break
                            
                            if len(found_rows) >= 5:
                                break
                
                if len(found_rows) >= 5:
                    break
        
        if found_rows:
            print(f"\nFound {len(found_rows)} matching rows in PDF:")
            for i, row_info in enumerate(found_rows, 1):
                print(f"\n  Row {i} (Page {row_info['page']}):")
                print(f"    PT Code: {row_info['pt_code']}")
                print(f"    Date: {row_info['date']}")
                print(f"    Column 10: '{row_info['procedure_col10']}'")
                print(f"    Column 11: '{row_info['procedure_col11']}'")
                print(f"    Procedure Code Found: {row_info['procedure_found'] if row_info['procedure_found'] else 'NOT FOUND'}")
                print(f"    First 15 columns: {row_info['full_row'][:15]}")
        else:
            print(f"\nNo matching rows found in first 20 pages of PDF")

# Check procedure code extraction patterns
print("\n" + "="*80)
print("CHECKING PDF PROCEDURE CODE PATTERNS")
print("="*80)

procedure_positions = {}  # Track where procedure codes actually appear

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages[:10], 1):  # Check first 10 pages
        tables = page.extract_tables()
        if tables:
            for table in tables:
                if table and len(table) > 1:
                    for row in table[1:]:
                        if not row:
                            continue
                        
                        # Check all columns for procedure code patterns (5-digit codes)
                        for col_idx in range(len(row)):
                            if col_idx < len(row) and row[col_idx]:
                                val = str(row[col_idx]).strip()
                                # Check if it's a 5-digit number (procedure code)
                                if val.isdigit() and len(val) == 5:
                                    if col_idx not in procedure_positions:
                                        procedure_positions[col_idx] = 0
                                    procedure_positions[col_idx] += 1

print(f"\nProcedure code positions found in PDF (first 10 pages):")
for col_idx, count in sorted(procedure_positions.items(), key=lambda x: x[1], reverse=True):
    print(f"  Column {col_idx}: {count} occurrences")

