#!/usr/bin/env python3
"""Analyze PDF structure to identify correct columns"""
import pdfplumber
import re

pdf_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\Transaction List 7.1.25-8.1.25.pdf"

with pdfplumber.open(pdf_path) as pdf:
    page1 = pdf.pages[0]
    tables = page1.extract_tables()
    
    if tables and len(tables) > 0:
        table = tables[0]
        
        print("="*80)
        print("ANALYZING PDF STRUCTURE")
        print("="*80)
        
        # Show header
        if len(table) > 0:
            print(f"\nHeader row ({len(table[0])} columns):")
            headers = [str(cell).strip() if cell else "" for cell in table[0]]
            for idx, header in enumerate(headers):
                if header:
                    print(f"  Col {idx}: '{header}'")
        
        # Analyze first 10 data rows to find patterns
        print(f"\n\nAnalyzing first 10 data rows:")
        print("="*80)
        
        for row_idx in range(1, min(11, len(table))):
            row = table[row_idx]
            if not row:
                continue
                
            print(f"\nRow {row_idx} (Excel row {row_idx + 1}):")
            
            # Show all non-empty columns
            non_empty_cols = []
            for col_idx, cell in enumerate(row):
                if cell and str(cell).strip():
                    cell_str = str(cell).strip()
                    # Identify what type of data this is
                    data_type = "unknown"
                    
                    # Check if date
                    if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', cell_str):
                        data_type = "DATE"
                    # Check if PT code (letters+numbers)
                    elif re.match(r'^[A-Z]{2,7}\d{3,}$', cell_str.upper()):
                        data_type = "PT_CODE"
                    # Check if numeric only
                    elif cell_str.isdigit():
                        if len(cell_str) == 2:
                            data_type = "MODIFIER? (2-digit)"
                        elif len(cell_str) == 1:
                            data_type = "DIAGNOSIS? (1-digit)"
                        elif len(cell_str) == 5:
                            data_type = "PROCEDURE_CODE? (5-digit)"
                        elif len(cell_str) >= 4:
                            data_type = "NUMBER"
                        else:
                            data_type = "NUMBER"
                    # Check if procedure code pattern
                    elif re.match(r'^\d{5}$', cell_str):
                        data_type = "PROCEDURE_CODE"
                    # Check if modifier (usually 2 digits or letter+digit)
                    elif re.match(r'^[0-9]{1,2}$|^[A-Z][0-9]$', cell_str.upper()):
                        data_type = "MODIFIER"
                    # Check if provider (letters)
                    elif re.match(r'^[A-Z]{1,4}$', cell_str.upper()):
                        data_type = "PROVIDER/COUNSELOR"
                    # Check if amount
                    elif re.match(r'^\d+\.\d{2}$', cell_str):
                        data_type = "AMOUNT"
                    else:
                        data_type = "TEXT"
                    
                    non_empty_cols.append((col_idx, cell_str, data_type))
            
            for col_idx, cell_str, data_type in non_empty_cols:
                print(f"  Col {col_idx:2d}: '{cell_str:20s}' [{data_type}]")
        
        # Analyze patterns across multiple rows
        print(f"\n\n" + "="*80)
        print("PATTERN ANALYSIS (first 10 rows):")
        print("="*80)
        
        # Find which column consistently has dates
        date_cols = {}
        pt_code_cols = {}
        modifier_cols = {}
        procedure_cols = {}
        provider_cols = {}
        amount_cols = {}
        
        for row_idx in range(1, min(11, len(table))):
            row = table[row_idx]
            if not row:
                continue
            
            for col_idx, cell in enumerate(row):
                if not cell:
                    continue
                cell_str = str(cell).strip()
                
                if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', cell_str):
                    date_cols[col_idx] = date_cols.get(col_idx, 0) + 1
                elif re.match(r'^[A-Z]{2,7}\d{3,}$', cell_str.upper()):
                    pt_code_cols[col_idx] = pt_code_cols.get(col_idx, 0) + 1
                elif re.match(r'^\d{5}$', cell_str):
                    procedure_cols[col_idx] = procedure_cols.get(col_idx, 0) + 1
                elif re.match(r'^[0-9]{1,2}$|^[A-Z][0-9]$', cell_str.upper()) and len(cell_str) <= 3:
                    modifier_cols[col_idx] = modifier_cols.get(col_idx, 0) + 1
                elif re.match(r'^[A-Z]{1,4}$', cell_str.upper()) and len(cell_str) <= 4:
                    provider_cols[col_idx] = provider_cols.get(col_idx, 0) + 1
                elif re.match(r'^\d+\.\d{2}$', cell_str):
                    amount_cols[col_idx] = amount_cols.get(col_idx, 0) + 1
        
        print(f"\nDate columns (appears in multiple rows): {sorted(date_cols.items(), key=lambda x: x[1], reverse=True)}")
        print(f"PT Code columns: {sorted(pt_code_cols.items(), key=lambda x: x[1], reverse=True)}")
        print(f"Procedure Code columns: {sorted(procedure_cols.items(), key=lambda x: x[1], reverse=True)}")
        print(f"Modifier columns: {sorted(modifier_cols.items(), key=lambda x: x[1], reverse=True)}")
        print(f"Provider/Counselor columns: {sorted(provider_cols.items(), key=lambda x: x[1], reverse=True)}")
        print(f"Amount columns: {sorted(amount_cols.items(), key=lambda x: x[1], reverse=True)}")

