#!/usr/bin/env python3
"""Deep check of PDF modifier extraction"""
import pdfplumber
import re

pdf_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\Transaction List 7.1.25-8.1.25.pdf"

rows_with_modifiers = 0
rows_without_modifiers = 0
rows_total = 0
modifier_values = {}
rows_missing_modifiers = []

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    print("="*80)
    
    for page_num, page in enumerate(pdf.pages[:10], 1):  # Check first 10 pages
        tables = page.extract_tables()
        if tables:
            for table in tables:
                if table and len(table) > 1:
                    for row_idx, row in enumerate(table[1:], 1):
                        rows_total += 1
                        
                        if not row:
                            continue
                        
                        # Extract fields
                        pt_code = ""
                        date = ""
                        modifier = ""
                        procedure_code = ""
                        
                        # Column 1: Date
                        if 1 < len(row) and row[1]:
                            date_val = str(row[1]).strip()
                            if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', date_val):
                                date = date_val
                        
                        # Column 4: PT Code
                        if 4 < len(row) and row[4]:
                            pt_val = str(row[4]).strip().upper()
                            if re.match(r'^[A-Z]{2,7}\d{3,}$', pt_val):
                                pt_code = pt_val
                        
                        # Column 10: Procedure Code
                        if 10 < len(row) and row[10]:
                            proc_val = str(row[10]).strip()
                            if proc_val.isdigit() and len(proc_val) == 5:
                                procedure_code = proc_val
                        
                        # Column 12: Modifier
                        if 12 < len(row) and row[12]:
                            mod_val = str(row[12]).strip()
                            # Check all possible modifier formats
                            if mod_val:
                                # Validate it's a modifier (1-2 digits or alphanumeric)
                                if re.match(r'^[0-9]{1,2}$|^[A-Z][0-9]$', mod_val.upper()) and len(mod_val) <= 3:
                                    modifier = mod_val
                                else:
                                    # Check if it might be a number stored as text
                                    try:
                                        num = float(mod_val)
                                        if 0 <= num <= 99:
                                            modifier = str(int(num))
                                    except:
                                        pass
                        
                        # Track modifiers
                        if modifier:
                            rows_with_modifiers += 1
                            modifier_values[modifier] = modifier_values.get(modifier, 0) + 1
                        else:
                            rows_without_modifiers += 1
                            if rows_without_modifiers <= 20 and pt_code:  # Show first 20 examples
                                # Check what's actually in column 12
                                col12_val = str(row[12]).strip() if 12 < len(row) and row[12] else "EMPTY"
                                rows_missing_modifiers.append({
                                    'page': page_num,
                                    'pt_code': pt_code,
                                    'date': date,
                                    'procedure': procedure_code,
                                    'col12_raw': col12_val,
                                    'row_data': [str(cell)[:20] for cell in row[:15]] if row else []
                                })

print(f"\n{'='*80}")
print("PDF MODIFIER EXTRACTION SUMMARY (first 10 pages)")
print(f"{'='*80}")
print(f"Total rows checked: {rows_total}")
print(f"Rows with valid modifiers: {rows_with_modifiers} ({rows_with_modifiers/rows_total*100:.1f}%)")
print(f"Rows without modifiers: {rows_without_modifiers} ({rows_without_modifiers/rows_total*100:.1f}%)")
print(f"\nModifier distribution:")
for mod, count in sorted(modifier_values.items(), key=lambda x: x[1], reverse=True):
    print(f"  '{mod}': {count}")

if rows_missing_modifiers:
    print(f"\nFirst 10 rows WITHOUT modifiers (showing column 12 content):")
    for i, row_info in enumerate(rows_missing_modifiers[:10], 1):
        print(f"\n  Row {i} (Page {row_info['page']}):")
        print(f"    PT Code: {row_info['pt_code']}")
        print(f"    Date: {row_info['date']}")
        print(f"    Procedure: {row_info['procedure']}")
        print(f"    Column 12 raw value: '{row_info['col12_raw']}'")
        print(f"    First 15 columns: {row_info['row_data']}")

# Check entire PDF
print(f"\n{'='*80}")
print("CHECKING ENTIRE PDF...")
print(f"{'='*80}")

total_rows_all = 0
total_with_modifiers_all = 0
total_without_modifiers_all = 0

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        if tables:
            for table in tables:
                if table and len(table) > 1:
                    for row in table[1:]:
                        total_rows_all += 1
                        
                        if not row or len(row) <= 12:
                            total_without_modifiers_all += 1
                            continue
                        
                        # Column 12: Modifier
                        modifier = ""
                        if 12 < len(row) and row[12]:
                            mod_val = str(row[12]).strip()
                            if mod_val:
                                if re.match(r'^[0-9]{1,2}$|^[A-Z][0-9]$', mod_val.upper()) and len(mod_val) <= 3:
                                    modifier = mod_val
                                else:
                                    try:
                                        num = float(mod_val)
                                        if 0 <= num <= 99:
                                            modifier = str(int(num))
                                    except:
                                        pass
                        
                        if modifier:
                            total_with_modifiers_all += 1
                        else:
                            total_without_modifiers_all += 1

print(f"\nENTIRE PDF SUMMARY:")
print(f"Total rows: {total_rows_all}")
print(f"Rows with modifiers: {total_with_modifiers_all} ({total_with_modifiers_all/total_rows_all*100:.1f}%)")
print(f"Rows without modifiers: {total_without_modifiers_all} ({total_without_modifiers_all/total_rows_all*100:.1f}%)")

