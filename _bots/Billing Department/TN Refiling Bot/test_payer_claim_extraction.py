#!/usr/bin/env python3
"""
Test script to extract Payer Claim Control # for a specific client from PDF
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
            print(f"PDF opened: {len(pdf.pages)} page(s)")
            
            # Extract text from all pages
            full_text = ""
            pages_text = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                full_text += page_text
                full_text += "\n"
                pages_text.append((page_num, page_text))
                print(f"Page {page_num}: {len(page_text)} characters extracted")
            
            print(f"\nTotal text extracted: {len(full_text)} characters\n")
            
            # If no text, might need OCR (but this PDF seems to have text)
            if not full_text.strip():
                print("WARNING: No text extracted - PDF may need OCR")
                return None
            
            # Split into lines for analysis
            lines = full_text.split('\n')
            
            # Normalize target client name for matching
            target_normalized = target_client_name.lower().strip()
            target_parts = [p.strip() for p in target_normalized.split()]
            
            print(f"Target client: {target_client_name}")
            print(f"Normalized: {target_parts}\n")
            
            # Pattern for Payer Claim Control # - common formats:
            # "Payer Claim Control #: 123456789"
            # "Payer Claim Control #123456789"
            # "Payer Claim Control # 123456789"
            # "Payer Claim Control Number: 123456789"
            payer_claim_patterns = [
                r'(?:payer\s*)?(?:claim\s*)?(?:control\s*)?(?:#|number|num)?\s*:?\s*(\d+)',
                r'payer\s*claim\s*control\s*[#:]?\s*(\d+)',
                r'control\s*[#:]?\s*(\d+)',
            ]
            
            # Strategy: Find all claims and their associated Payer Claim Control #s
            # Then match them to clients
            
            results = []
            current_claim = None
            current_client = None
            current_payer_claim_control = None
            
            # Look for structure: Claim sections with Patient names and Payer Claim Control #s
            for i, line in enumerate(lines):
                line_clean = line.strip()
                if not line_clean:
                    continue
                
                # Look for Claim # pattern (e.g., "Claim #148902694")
                claim_match = re.search(r'claim\s*#?\s*(\d+)', line_clean, re.IGNORECASE)
                if claim_match:
                    if current_claim and current_client and current_payer_claim_control:
                        # Save previous claim data
                        results.append({
                            'claim': current_claim,
                            'client': current_client,
                            'payer_claim_control': current_payer_claim_control
                        })
                    current_claim = claim_match.group(1)
                    current_client = None
                    current_payer_claim_control = None
                    print(f"Found Claim #{current_claim} at line {i+1}")
                
                # Look for "Patient:" line with client name
                if 'patient' in line_clean.lower() and ':' in line_clean:
                    patient_match = re.search(r'patient\s*:?\s*(.+)', line_clean, re.IGNORECASE)
                    if patient_match:
                        patient_name = patient_match.group(1).strip()
                        # Clean up patient name (remove patient ID if present)
                        patient_name = re.sub(r'\s*-?\s*[A-Z0-9]+$', '', patient_name).strip()
                        current_client = patient_name
                        print(f"  Found Patient: {current_client} (line {i+1})")
                
                # Look for Payer Claim Control # in current section
                for pattern in payer_claim_patterns:
                    match = re.search(pattern, line_clean, re.IGNORECASE)
                    if match:
                        potential_control = match.group(1).strip()
                        # Validate it's a reasonable number (usually 6-20 digits)
                        if len(potential_control) >= 6 and len(potential_control) <= 20:
                            current_payer_claim_control = potential_control
                            print(f"  Found Payer Claim Control #: {current_payer_claim_control} (line {i+1})")
                            break
                
                # Also look for client name directly in lines (for claim sections)
                # Check if this line contains the target client name
                line_lower = line_clean.lower()
                if any(part in line_lower for part in target_parts if len(part) > 2):
                    # More careful match - check if all significant parts of name are present
                    name_match_score = sum(1 for part in target_parts if len(part) > 2 and part in line_lower)
                    if name_match_score >= 2:  # At least 2 parts match
                        # Extract potential client name from line
                        potential_name = None
                        # Look for "Patient: Name" or just name patterns
                        if 'patient' in line_lower and ':' in line_clean:
                            potential_name = line_clean.split(':', 1)[1].strip()
                            # Remove patient ID if present
                            potential_name = re.sub(r'\s*-?\s*[A-Z0-9]+$', '', potential_name).strip()
                        else:
                            # Try to extract name from line (capitalized words)
                            name_parts = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b', line_clean)
                            if len(name_parts) >= 2:
                                potential_name = ' '.join(name_parts[:2])
                        
                        if potential_name:
                            potential_normalized = potential_name.lower()
                            # Check if it matches target
                            potential_parts = [p.strip() for p in potential_normalized.split()]
                            if all(any(target_part in p or p in target_part for p in potential_parts) 
                                   for target_part in target_parts if len(target_part) > 2):
                                if not current_client or target_client_name.lower() in potential_normalized:
                                    current_client = potential_name
                                    print(f"  Matched client name: {current_client} (line {i+1})")
            
            # Save last claim if exists
            if current_claim and current_client and current_payer_claim_control:
                results.append({
                    'claim': current_claim,
                    'client': current_client,
                    'payer_claim_control': current_payer_claim_control
                })
            
            print(f"\n{'='*80}")
            print(f"EXTRACTION RESULTS:")
            print(f"{'='*80}\n")
            
            for result in results:
                print(f"Claim #{result['claim']}:")
                print(f"  Client: {result['client']}")
                print(f"  Payer Claim Control #: {result['payer_claim_control']}")
                print()
            
            # Find matching client
            target_result = None
            for result in results:
                client_normalized = result['client'].lower()
                # Check if target client name matches
                if all(any(part in client_normalized for part in target_parts if len(part) > 2) 
                       for target_part in target_parts if len(target_part) > 2):
                    if target_result is None or len(target_result['client'].split()) < len(result['client'].split()):
                        target_result = result
            
            # More specific match - look for exact or very close match
            if target_result:
                # Try to find best match
                best_match = None
                best_score = 0
                
                for result in results:
                    client_parts = [p.lower().strip() for p in result['client'].split()]
                    score = sum(1 for target_part in target_parts 
                              for client_part in client_parts 
                              if target_part in client_part or client_part in target_part)
                    if score > best_score:
                        best_score = score
                        best_match = result
                
                if best_match:
                    target_result = best_match
            
            if target_result:
                print(f"{'='*80}")
                print(f"✅ FOUND MATCH:")
                print(f"{'='*80}")
                print(f"Target Client: {target_client_name}")
                print(f"Matched Client: {target_result['client']}")
                print(f"Claim #: {target_result['claim']}")
                print(f"Payer Claim Control #: {target_result['payer_claim_control']}")
                print(f"{'='*80}\n")
                
                return {
                    'client_name': target_result['client'],
                    'claim_number': target_result['claim'],
                    'payer_claim_control': target_result['payer_claim_control'],
                    'matched': True
                }
            else:
                print(f"{'='*80}")
                print(f"❌ NO MATCH FOUND")
                print(f"{'='*80}")
                print(f"Target Client: {target_client_name}")
                print(f"Available clients in PDF:")
                for result in results:
                    print(f"  - {result['client']}")
                print(f"{'='*80}\n")
                
                return {
                    'client_name': target_client_name,
                    'payer_claim_control': None,
                    'matched': False,
                    'available_clients': [r['client'] for r in results]
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
            print(f"\n🎉 SUCCESS! Found Payer Claim Control #: {result['payer_claim_control']}")
        else:
            print(f"\n⚠️ Could not find exact match for '{target_client}'")
    else:
        print("\n❌ Extraction failed")

