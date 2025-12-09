#!/usr/bin/env python3
"""Check total rows in PDF"""
import pdfplumber

pdf_path = r"G:\Company\Billing Dept\Medicare Modifier Refiling Excel\Transaction List 7.1.25-8.1.25.pdf"

total_rows = 0
with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    print("\n" + "="*80)
    
    for page_num in range(len(pdf.pages)):
        page = pdf.pages[page_num]
        tables = page.extract_tables()
        page_rows = 0
        
        for table in tables:
            if table and len(table) > 1:
                # Subtract header row
                table_data_rows = len(table) - 1
                page_rows += table_data_rows
        
        total_rows += page_rows
        
        if page_num < 5 or page_num >= len(pdf.pages) - 5:
            print(f"Page {page_num+1}: {len(tables)} table(s), {page_rows} data row(s)")
    
    print("\n" + "="*80)
    print(f"Total data rows across all pages: {total_rows}")

