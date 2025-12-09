#!/usr/bin/env python3
"""
Improved test script to extract Payer Claim Control # for a specific client
Analyzes PDF structure more carefully
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
                print(f"Page {page_num}: {len(page_text)} characters extracted")
            
            print(f"\nTotal text extracted: {len(full_text)} characters\n")
            
            if not full_text.strip():
                print("WARNING: No text extracted - PDF may need OCR")
                return None
            
            # Split into lines
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # Normalize target client name
            target_normalized = target_client_name.lower().strip()
            target_parts = [p.strip().lower() for p in target_normalized.split() if len(p.strip()) > 1]
            
            print(f"Target client: {target_client_name}")
            print(f"Target parts: {target_parts}\n")
            
            # Print all lines for analysis
            print("=== ANALYZING PDF STRUCTURE ===")
            print(f"Total lines: {len(lines)}\n")
            
            # Look for all potential client names and their contexts
            print("=== SEARCHING FOR CLIENT NAMES AND PAYER CLAIM CONTROL NUMBERS ===\n")
            
            # Pattern for Payer Claim Control # - try multiple formats
            payer_patterns = [
                r'(?:payer\s*)?(?:claim\s*)?(?:control\s*)?[#:]?\s*(\d{6,20})',  # 6-20 digit numbers
                r'control[#:]?\s*(\d{6,20})',
            ]
            
            # Also look for ERA # which might be the Payer Claim Control #
            era_pattern = r'ERA\s*#?\s*(\d+)'
            
            # Structure: Each claim section has:
            # - Claim #XXXXX
            # - Patient: NAME - ID
            # - Payer Claim Control #: XXXX (might be near claim or patient)
            
            claims_data = []
            current_claim_num = None
            current_patient = None
            current_patient_id = None
            
            # Also track ERA number (might be at top of page)
            era_number = None
            era_match = re.search(era_pattern, full_text, re.IGNORECASE)
            if era_match:
                era_number = era_match.group(1)
                print(f"Found ERA # at document level: {era_number}")
            
            print("Scanning for claims and patients...\n")
            
            for i, line in enumerate(lines):
                # Look for Claim # pattern
                claim_match = re.search(r'claim\s*#?\s*(\d+)', line, re.IGNORECASE)
                if claim_match:
                    # Save previous claim if exists
                    if current_claim_num:
                        claims_data.append({
                            'claim': current_claim_num,
                            'patient': current_patient,
                            'patient_id': current_patient_id,
                            'payer_claim_control': None  # Will find separately
                        })
                    
                    current_claim_num = claim_match.group(1)
                    print(f"Found Claim #{current_claim_num} at line {i+1}: {line[:80]}")
                
                # Look for Patient: pattern
                patient_match = re.search(r'patient\s*:?\s*(.+?)(?:\s*-\s*([A-Z0-9]+))?', line, re.IGNORECASE)
                if patient_match:
                    patient_name = patient_match.group(1).strip()
                    patient_id = patient_match.group(2).strip() if patient_match.group(2) else None
                    
                    # Clean patient name
                    patient_name = re.sub(r'\s+', ' ', patient_name).strip()
                    
                    current_patient = patient_name
                    current_patient_id = patient_id
                    print(f"  -> Patient: {current_patient} (ID: {current_patient_id})")
                
                # Look for Payer Claim Control # in nearby lines
                for pattern in payer_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        control_num = match.group(1)
                        print(f"  -> Found Payer Claim Control #: {control_num} (line {i+1})")
                        # Associate with current claim if exists
                        if current_claim_num and current_patient:
                            # Update last added claim or add new
                            if claims_data and claims_data[-1].get('claim') == current_claim_num:
                                claims_data[-1]['payer_claim_control'] = control_num
                            else:
                                claims_data.append({
                                    'claim': current_claim_num,
                                    'patient': current_patient,
                                    'patient_id': current_patient_id,
                                    'payer_claim_control': control_num
                                })
            
            # Save last claim
            if current_claim_num:
                claims_data.append({
                    'claim': current_claim_num,
                    'patient': current_patient,
                    'patient_id': current_patient_id,
                    'payer_claim_control': None
                })
            
            print(f"\n{'='*80}")
            print("ALL CLAIMS FOUND:")
            print(f"{'='*80}\n")
            
            for claim_data in claims_data:
                print(f"Claim #{claim_data['claim']}:")
                print(f"  Patient: {claim_data['patient']}")
                print(f"  Patient ID: {claim_data['patient_id']}")
                print(f"  Payer Claim Control #: {claim_data.get('payer_claim_control', 'Not found')}")
                print()
            
            # Now search more specifically for Vernell E Luckey
            print(f"{'='*80}")
            print(f"SEARCHING FOR: {target_client_name}")
            print(f"{'='*80}\n")
            
            # Look through all claims for matching client
            matched_claims = []
            for claim_data in claims_data:
                if claim_data['patient']:
                    patient_normalized = claim_data['patient'].lower()
                    # Check if target parts match
                    match_score = sum(1 for target_part in target_parts 
                                    if target_part in patient_normalized)
                    if match_score >= len(target_parts) - 1:  # Allow one missing part
                        matched_claims.append(claim_data)
                        print(f"POTENTIAL MATCH:")
                        print(f"  Claim #{claim_data['claim']}: {claim_data['patient']}")
                        print(f"  Payer Claim Control #: {claim_data.get('payer_claim_control', 'Not found')}")
                        print(f"  Match score: {match_score}/{len(target_parts)}")
                        print()
            
            # Also search text more directly for "Vernell" and "Luckey"
            print("Direct text search for 'Vernell' and 'Luckey'...\n")
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if 'vernell' in line_lower or 'luckey' in line_lower:
                    print(f"Line {i+1}: {line}")
                    # Look for numbers nearby (might be Payer Claim Control #)
                    numbers_in_line = re.findall(r'\d{6,}', line)
                    if numbers_in_line:
                        print(f"  -> Found numbers: {numbers_in_line}")
                    # Check context (previous and next lines)
                    if i > 0:
                        prev_line = lines[i-1]
                        prev_numbers = re.findall(r'\d{6,}', prev_line)
                        if prev_numbers:
                            print(f"  -> Previous line numbers: {prev_numbers}")
                    if i < len(lines) - 1:
                        next_line = lines[i+1]
                        next_numbers = re.findall(r'\d{6,}', next_line)
                        if next_numbers:
                            print(f"  -> Next line numbers: {next_numbers}")
                    print()
            
            # Best match
            if matched_claims:
                best_match = matched_claims[0]
                print(f"{'='*80}")
                print(f"✅ BEST MATCH FOUND:")
                print(f"{'='*80}")
                print(f"Target: {target_client_name}")
                print(f"Matched: {best_match['patient']}")
                print(f"Claim #: {best_match['claim']}")
                print(f"Payer Claim Control #: {best_match.get('payer_claim_control', 'Not found in structured data')}")
                print(f"{'='*80}\n")
                
                return {
                    'client_name': best_match['patient'],
                    'claim_number': best_match['claim'],
                    'payer_claim_control': best_match.get('payer_claim_control'),
                    'matched': True
                }
            else:
                print(f"{'='*80}")
                print(f"❌ NO STRUCTURED MATCH FOUND")
                print(f"{'='*80}\n")
                
                return {
                    'client_name': target_client_name,
                    'payer_claim_control': None,
                    'matched': False,
                    'all_claims': claims_data
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
    
    if result:
        if result.get('matched'):
            print(f"\n🎉 SUCCESS! Payer Claim Control #: {result.get('payer_claim_control', 'Not found')}")
        else:
            print(f"\n⚠️ No structured match found")
            if result.get('all_claims'):
                print(f"\nFound {len(result['all_claims'])} claims in PDF")
                print("Check the output above for potential matches")
    else:
        print("\n❌ Extraction failed")

