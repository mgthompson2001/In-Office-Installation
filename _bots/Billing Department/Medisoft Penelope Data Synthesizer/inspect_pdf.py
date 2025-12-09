#!/usr/bin/env python3
"""Quick script to inspect PDF structure"""
import pdfplumber

pdf_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\Transaction List 7.1.25-8.1.25.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    print("\n" + "="*80)
    
    # Check first page
    page1 = pdf.pages[0]
    tables = page1.extract_tables()
    print(f"\nPage 1: Found {len(tables)} table(s)")
    
    for table_idx, table in enumerate(tables):
        if not table or len(table) == 0:
            continue
            
        print(f"\n{'='*80}")
        print(f"Table {table_idx + 1} on Page 1:")
        print(f"Total rows: {len(table)}")
        
        if len(table) > 0:
            print(f"\nHeaders ({len(table[0])} columns):")
            headers = [str(cell).strip() if cell else "" for cell in table[0]]
            for idx, header in enumerate(headers):
                print(f"  Column {idx}: '{header}'")
        
        print(f"\nFirst 5 data rows:")
        for row_idx in range(1, min(6, len(table))):
            row = table[row_idx]
            print(f"\n  Row {row_idx} ({len(row) if row else 0} cells):")
            if row:
                for col_idx, cell in enumerate(row[:10]):  # First 10 columns
                    cell_str = str(cell).strip() if cell else ""
                    if len(cell_str) > 50:
                        cell_str = cell_str[:47] + "..."
                    print(f"    Col {col_idx} ('{headers[col_idx] if col_idx < len(headers) else ''}'): '{cell_str}'")
    
    # Check a few more pages to see pattern
    print(f"\n{'='*80}")
    print("\nChecking pages 2-5 for row counts:")
    for page_num in range(1, min(6, len(pdf.pages))):
        page = pdf.pages[page_num]
        tables = page.extract_tables()
        total_rows = 0
        for table in tables:
            if table and len(table) > 1:
                total_rows += len(table) - 1  # Subtract header
        print(f"Page {page_num + 1}: {len(tables)} table(s), {total_rows} data row(s)")

