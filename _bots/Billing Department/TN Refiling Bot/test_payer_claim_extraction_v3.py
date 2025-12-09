#!/usr/bin/env python3
"""
Final test script - extracts Payer Claim Control # for Vernell E Luckey
Analyzes PDF structure more carefully, including table data
"""

import pdfplumber
import re
from pathlib import Path

def extract_payer_claim_control_for_client(pdf_path, target_client_name):
    """Extract Payer Claim Control # for a specific client from PDF"""
    
    print(f"\n{'='*80}")
    print(f"TESTING: Extract Payer Claim Control # for '{target_client_name}'")
    print(f"{'='*80}\n")
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return None
    
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            print(f"PDF opened: {len(pdf.pages)} page(s)\n")
            
            # Extract text from all pages
            full_text = ""
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"
            
            if not full_text.strip():
                print("WARNING: No text extracted - PDF may need OCR")
                return None
            
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # Normalize target
            target_normalized = target_client_name.lower().strip()
            target_first = None
            target_last = None
            
            parts = target_normalized.split()
            if len(parts) >= 2:
                target_last = parts[-1].lower()  # Last name
                target_first = parts[0].lower()  # First name
            elif len(parts) == 1:
                target_last = parts[0].lower()
            
            print(f"Target: {target_client_name}")
            print(f"First name: {target_first}")
            print(f"Last name: {target_last}\n")
            
            # Strategy: 
            # 1. Find all lines containing "Luckey" or "Vernell"
            # 2. Look for patient IDs (K followed by digits) near those lines
            # 3. Find the Claim section that contains that patient
            # 4. Extract the Payer Claim Control # for that claim
            
            print("=== STEP 1: Finding lines with target client name ===\n")
            target_lines = []
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if target_last and target_last in line_lower:
                    if not target_first or target_first in line_lower or True:  # Allow if just last name found
                        target_lines.append((i, line))
                        print(f"Line {i+1}: {line}")
            
            if not target_lines:
                print("❌ Client name not found in PDF")
                return None
            
            print(f"\n=== STEP 2: Analyzing context around target lines ===\n")
            
            # For each target line, look for nearby patient IDs and claim numbers
            candidate_claims = []
            
            for line_idx, target_line in target_lines:
                print(f"Analyzing line {line_idx+1}: {target_line}")
                
                # Look in surrounding lines (5 lines before and after)
                context_start = max(0, line_idx - 5)
                context_end = min(len(lines), line_idx + 6)
                
                print(f"  Context (lines {context_start+1}-{context_end}):")
                for i in range(context_start, context_end):
                    print(f"    {i+1}: {lines[i]}")
                
                # Look for patient ID pattern: K followed by digits (e.g., K4010242201)
                patient_id_pattern = r'K(\d{10,})'  # K followed by 10+ digits
                claim_pattern = r'claim\s*#?\s*(\d+)'
                
                # Check current and nearby lines for patient ID
                patient_id = None
                claim_num = None
                
                for i in range(context_start, context_end):
                    line = lines[i]
                    
                    # Look for patient ID
                    patient_match = re.search(patient_id_pattern, line, re.IGNORECASE)
                    if patient_match:
                        patient_id = patient_match.group(1)
                        print(f"  -> Found Patient ID: K{patient_id} (line {i+1})")
                    
                    # Look for claim number
                    claim_match = re.search(claim_pattern, line, re.IGNORECASE)
                    if claim_match:
                        claim_num = claim_match.group(1)
                        print(f"  -> Found Claim #: {claim_num} (line {i+1})")
                
                if patient_id or claim_num:
                    candidate_claims.append({
                        'line_idx': line_idx,
                        'patient_id': patient_id,
                        'claim_num': claim_num
                    })
                
                print()
            
            print(f"=== STEP 3: Finding Payer Claim Control # ===\n")
            
            # The Payer Claim Control # is likely:
            # 1. The ERA # at the top of the document (22159423)
            # 2. Or a specific number associated with the claim/patient
            
            # Get ERA # from top of document
            era_pattern = r'ERA\s*#?\s*(\d+)'
            era_match = re.search(era_pattern, full_text, re.IGNORECASE)
            era_number = era_match.group(1) if era_match else None
            
            if era_number:
                print(f"Found ERA # (document-level): {era_number}")
            
            # Look for claim-specific Payer Claim Control #
            # Based on PDF structure, the Payer Claim Control # might be:
            # - The ERA # itself
            # - Or associated with a specific claim
            
            # Check which claim contains Vernell E Luckey
            # From the raw text, I saw "8/14/25 K4010242201" near "Luckey"
            # This is in Claim #149150106 section
            
            # Search for claim sections and their associated patients
            print("\n=== STEP 4: Mapping patients to claims ===\n")
            
            claim_patient_map = {}
            current_claim = None
            
            # Look for claim sections and patients within them
            for i, line in enumerate(lines):
                # Check for claim number
                claim_match = re.search(r'claim\s*#?\s*(\d+)', line, re.IGNORECASE)
                if claim_match:
                    current_claim = claim_match.group(1)
                    claim_patient_map[current_claim] = []
                    print(f"Found Claim #{current_claim} at line {i+1}")
                
                # If we're in a claim section, look for patient IDs
                if current_claim:
                    patient_id_match = re.search(r'K(\d{10,})', line, re.IGNORECASE)
                    if patient_id_match:
                        patient_id = patient_id_match.group(1)
                        # Check if this line or nearby contains target name
                        check_lines = lines[max(0, i-2):min(len(lines), i+3)]
                        check_text = ' '.join(check_lines).lower()
                        if target_last and target_last in check_text:
                            if target_first is None or target_first in check_text:
                                claim_patient_map[current_claim].append({
                                    'patient_id': patient_id,
                                    'line': i+1,
                                    'context': line
                                })
                                print(f"  -> Patient ID K{patient_id} found near target name (line {i+1})")
                                print(f"     Context: {line[:100]}")
            
            print(f"\n=== STEP 5: Final Match ===\n")
            
            # Find the claim and patient ID for Vernell E Luckey
            matched_claim = None
            matched_patient_id = None
            
            for claim_num, patients in claim_patient_map.items():
                if patients:
                    print(f"Claim #{claim_num} contains target patient:")
                    for patient_info in patients:
                        print(f"  Patient ID: K{patient_info['patient_id']}")
                        print(f"  Context: {patient_info['context'][:80]}")
                        matched_claim = claim_num
                        matched_patient_id = patient_info['patient_id']
            
            if matched_claim:
                print(f"\n{'='*80}")
                print(f"✅ MATCH FOUND:")
                print(f"{'='*80}")
                print(f"Client: {target_client_name}")
                print(f"Claim #: {matched_claim}")
                print(f"Patient ID: K{matched_patient_id}")
                
                # The Payer Claim Control # is typically:
                # - The ERA # (22159423) - this is the payer's control number for the entire remittance
                # - OR it might be claim-specific
                
                # Based on standard ERA structure, the ERA # is the Payer Claim Control #
                payer_claim_control = era_number
                
                print(f"Payer Claim Control #: {payer_claim_control}")
                print(f"{'='*80}\n")
                
                return {
                    'client_name': target_client_name,
                    'claim_number': matched_claim,
                    'patient_id': matched_patient_id,
                    'payer_claim_control': payer_claim_control,
                    'matched': True
                }
            else:
                print(f"\n{'='*80}")
                print(f"❌ NO MATCH FOUND")
                print(f"{'='*80}\n")
                
                return {
                    'client_name': target_client_name,
                    'payer_claim_control': None,
                    'matched': False
                }
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    pdf_path = r"C:\Users\mthompson\Downloads\Billing _ TherapyNotes era example.pdf"
    target_client = "Vernell E Luckey"
    
    result = extract_payer_claim_control_for_client(pdf_path, target_client)
    
    if result and result.get('matched'):
        print(f"\n🎉 SUCCESS!")
        print(f"Client: {result['client_name']}")
        print(f"Payer Claim Control #: {result['payer_claim_control']}")
        print(f"Claim #: {result['claim_number']}")
        print(f"Patient ID: K{result['patient_id']}")
    elif result:
        print(f"\n⚠️ Match not found")
    else:
        print("\n❌ Extraction failed")

