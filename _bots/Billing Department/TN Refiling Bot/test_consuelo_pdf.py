#!/usr/bin/env python3
"""Test extraction from CONSUELO R PALENCIA PDF"""

import pdfplumber
import re
from pathlib import Path

pdf_path = r"C:\Users\mthompson\Downloads\ERA #22159423 details for CONSUELO R PALENCIA _ TherapyNotes.pdf"
target_client = "CONSUELO R PALENCIA"

print(f"\n{'='*80}")
print(f"TESTING: Extract Payer Claim Control # for '{target_client}'")
print(f"{'='*80}\n")

try:
    with pdfplumber.open(pdf_path) as pdf:
        # Extract text from all pages
        full_text = ""
        for page_num, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text() or ""
            full_text += page_text + "\n"
            print(f"Page {page_num}: {len(page_text)} characters")
        
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        print(f"\nTotal lines: {len(lines)}\n")
        
        # Search for "Claim Totals" and then look for "Payer Claim Control #:" after it
        print("=== SEARCHING FOR 'CLAIM TOTALS' AND 'PAYER CLAIM CONTROL #:' AFTER IT ===\n")
        
        found_claim_totals = False
        payer_claim_control_found = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            if 'claim totals' in line_lower:
                found_claim_totals = True
                print(f"✅ Found 'Claim Totals' on line {i+1}: {line}")
                print(f"\nChecking lines {i+1} to {min(i+20, len(lines))} for 'Payer Claim Control #:'\n")
                
                # Look for "Payer Claim Control #:" in the next 20 lines
                for j in range(i+1, min(i+20, len(lines))):
                    next_line = lines[j]
                    next_line_lower = next_line.lower()
                    
                    print(f"Line {j+1}: {next_line}")
                    
                    if 'payer claim control' in next_line_lower and ':' in next_line:
                        payer_claim_control_found = True
                        print(f"\n{'='*80}")
                        print(f"✅✅✅ FOUND PAYER CLAIM CONTROL # ON LINE {j+1}")
                        print(f"{'='*80}")
                        print(f"Line: {next_line}\n")
                        
                        # Extract the number
                        match = re.search(r'(?:payer\s*claim\s*control\s*#?\s*:?\s*)(.+)', next_line, re.IGNORECASE)
                        if match:
                            control_number = match.group(1).strip()
                            # Clean up - keep numbers, spaces, dashes, dots
                            control_number = re.sub(r'[^\d\s\-\.]+.*$', '', control_number).strip()
                            print(f"Extracted Payer Claim Control #: {control_number}")
                            print(f"{'='*80}\n")
                        break
                
                if not payer_claim_control_found:
                    print("⚠️ 'Payer Claim Control #:' not found within 20 lines after 'Claim Totals'")
                
                break
        
        if not found_claim_totals:
            print("⚠️ 'Claim Totals' not found in PDF")
            print("\nSearching for 'Payer Claim Control #:' anywhere in PDF:\n")
            for i, line in enumerate(lines):
                if 'payer claim control' in line.lower():
                    print(f"Line {i+1}: {line}")
        
        # Also search for all "Payer Claim Control #:" entries
        print(f"\n{'='*80}")
        print("ALL 'PAYER CLAIM CONTROL #:' ENTRIES IN PDF:")
        print(f"{'='*80}\n")
        
        all_found = []
        for i, line in enumerate(lines):
            if 'payer claim control' in line.lower() and ':' in line:
                match = re.search(r'(?:payer\s*claim\s*control\s*#?\s*:?\s*)(.+)', line, re.IGNORECASE)
                if match:
                    control_number = match.group(1).strip()
                    control_number = re.sub(r'[^\d\s\-\.]+.*$', '', control_number).strip()
                    all_found.append({
                        'line_num': i + 1,
                        'line': line,
                        'number': control_number
                    })
                    print(f"Line {i+1}: {line}")
                    print(f"  -> Extracted: {control_number}\n")
        
        if all_found:
            print(f"\n✅ Total 'Payer Claim Control #:' entries found: {len(all_found)}")
            print(f"✅ First entry: {all_found[0]['number']}")
        else:
            print("❌ No 'Payer Claim Control #:' entries found in PDF")
        
        # Now test the bot's extraction function
        print(f"\n{'='*80}")
        print("TESTING BOT'S EXTRACTION FUNCTION:")
        print(f"{'='*80}\n")
        
        # Import and test
        import sys
        from pathlib import Path
        bot_path = Path(__file__).parent / "tn_refiling_bot.py"
        if bot_path.exists():
            sys.path.insert(0, str(bot_path.parent))
            from tn_refiling_bot import TNRefilingBot
            import tkinter as tk
            
            root = tk.Tk()
            root.withdraw()
            bot = TNRefilingBot(root)
            
            result = bot.extract_payer_claim_control(pdf_path, target_client)
            
            print(f"\n{'='*80}")
            print("BOT EXTRACTION RESULT:")
            print(f"{'='*80}")
            if result:
                print(f"Payer Claim Control #: {result.get('payer_claim_control')}")
                print(f"Matched: {result.get('matched')}")
                print(f"Client Name: {result.get('client_name')}")
                print(f"Patient ID: {result.get('patient_id')}")
                print(f"Claim #: {result.get('claim_number')}")
            else:
                print("Result is None")
            print(f"{'='*80}\n")
            
            root.destroy()
        else:
            print("Bot file not found, skipping bot test")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

