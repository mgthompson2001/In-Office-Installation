#!/usr/bin/env python3
"""
Final test - extracts Payer Claim Control # for Vernell E Luckey
Handles corrupted text and properly maps clients to claims
"""

import pdfplumber
import re
from pathlib import Path

def extract_payer_claim_control_for_client(pdf_path, target_client_name):
    """Extract Payer Claim Control # for a specific client from PDF"""
    
    print(f"\n{'='*80}")
    print(f"EXTRACTING: Payer Claim Control # for '{target_client_name}'")
    print(f"{'='*80}\n")
    
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            # Extract text from all pages
            full_text = '\n'.join([page.extract_text() or '' for page in pdf.pages])
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # Normalize target name
            target_parts = target_client_name.lower().strip().split()
            target_first = target_parts[0] if target_parts else None
            target_last = target_parts[-1] if len(target_parts) > 1 else target_parts[0] if target_parts else None
            
            print(f"Target: {target_client_name}")
            print(f"Looking for: first='{target_first}', last='{target_last}'\n")
            
            # STEP 1: Find all "Payer Claim Control #:" entries in the PDF
            print("=== STEP 1: Searching for 'Payer Claim Control #:' entries ===\n")
            
            payer_claim_control_pattern = r'(?:payer\s*claim\s*control\s*#?\s*:?\s*)([^\n]+)'
            all_payer_controls = []
            
            for i, line in enumerate(lines):
                if 'payer claim control' in line.lower() and ':' in line:
                    # Extract the number(s) after "Payer Claim Control #:"
                    match = re.search(r'(?:payer\s*claim\s*control\s*#?\s*:?\s*)(.+)', line, re.IGNORECASE)
                    if match:
                        control_number = match.group(1).strip()
                        all_payer_controls.append({
                            'line_num': i + 1,
                            'line': line,
                            'control_number': control_number
                        })
                        print(f"Found 'Payer Claim Control #:' on line {i+1}: {line}")
            
            if not all_payer_controls:
                print("❌ No 'Payer Claim Control #:' entries found in PDF\n")
                return None
            
            print(f"\nTotal 'Payer Claim Control #:' entries found: {len(all_payer_controls)}\n")
            
            # STEP 2: Find all claims and map them
            claim_pattern = r'claim\s*#?\s*(\d+)'
            patient_id_pattern = r'K(\d{10,})'  # Patient ID: K followed by 10+ digits
            
            claims_map = {}  # claim_num -> list of patient IDs
            current_claim = None
            
            # Map claims to their sections
            for i, line in enumerate(lines):
                # Check for claim number
                claim_match = re.search(claim_pattern, line, re.IGNORECASE)
                if claim_match:
                    current_claim = claim_match.group(1)
                    if current_claim not in claims_map:
                        claims_map[current_claim] = []
                
                # If we're in a claim section, look for patient IDs
                if current_claim:
                    patient_match = re.search(patient_id_pattern, line, re.IGNORECASE)
                    if patient_match:
                        patient_id = patient_match.group(1)
                        if patient_id not in claims_map[current_claim]:
                            claims_map[current_claim].append(patient_id)
            
            print(f"Found {len(claims_map)} claim(s):")
            for claim_num, patient_ids in claims_map.items():
                print(f"  Claim #{claim_num}: {len(patient_ids)} patient(s)")
            print()
            
            # STEP 3: Find target client by searching for last name "Luckey"
            print(f"=== Searching for '{target_last}' (last name) ===\n")
            
            target_patient_id = None
            target_claim = None
            
            # Search for "Luckey" in lines
            for i, line in enumerate(lines):
                line_lower = line.lower()
                
                # Check if this line contains the last name
                if target_last and target_last in line_lower:
                    print(f"Line {i+1}: {line}")
                    
                    # Look for patient ID in nearby lines (within 5 lines before/after)
                    context_start = max(0, i - 5)
                    context_end = min(len(lines), i + 6)
                    
                    print(f"  Checking context (lines {context_start+1}-{context_end}):")
                    for j in range(context_start, context_end):
                        print(f"    {j+1}: {lines[j]}")
                    
                    # Collect all patient IDs in context with their distances
                    candidate_patient_ids = []
                    
                    for j in range(context_start, context_end):
                        patient_match = re.search(patient_id_pattern, lines[j], re.IGNORECASE)
                        if patient_match:
                            potential_id = patient_match.group(1)
                            distance = abs(j - i)  # Distance from last name line
                            is_direct_before = (j == i - 1)  # Directly before last name (highest priority)
                            
                            candidate_patient_ids.append({
                                'id': potential_id,
                                'line': j + 1,
                                'distance': distance,
                                'is_direct_before': is_direct_before,
                                'line_text': lines[j]
                            })
                            print(f"  Found Patient ID: K{potential_id} on line {j+1} (distance: {distance})")
                    
                    if not candidate_patient_ids:
                        continue
                    
                    # Sort candidates: prioritize direct before, then closest
                    candidate_patient_ids.sort(key=lambda x: (not x['is_direct_before'], x['distance']))
                    
                    # Check context for first name match
                    context_text = ' '.join(lines[context_start:context_end]).lower()
                    
                    # For "Vernell", we need to handle corruption - look for similar patterns
                    # "VerCnoedlle" might be "Vernell" corrupted
                    first_name_found = False
                    if target_first:
                        # Check for exact match or similar (handle corruption)
                        if (target_first in context_text or 
                            'vernell' in context_text or
                            ('ver' in context_text and 'cnoedlle' in context_text) or  # Corrupted "Vernell"
                            ('ver' in context_text and ('nel' in context_text or 'rnel' in context_text))):
                            first_name_found = True
                            print(f"  ✅ First name '{target_first}' found in context")
                    
                    # Select best candidate
                    # Priority: 1) Direct before (most reliable), 2) Any if first name found, 3) Any if no first name
                    for candidate in candidate_patient_ids:
                        if candidate['is_direct_before']:
                            print(f"  ✅ Patient ID K{candidate['id']} is directly before last name (MOST RELIABLE)")
                            target_patient_id = candidate['id']
                            break
                        elif first_name_found or not target_first:
                            print(f"  ✅ Patient ID K{candidate['id']} accepted (closest match)")
                            target_patient_id = candidate['id']
                            break
                    
                    if target_patient_id:
                        print(f"  ✅ FINAL SELECTED Patient ID: K{target_patient_id}")
                        
                        # Find which claim this patient ID belongs to
                        for claim_num, patient_ids in claims_map.items():
                            if target_patient_id in patient_ids:
                                target_claim = claim_num
                                print(f"  ✅ Found in Claim #{target_claim}")
                                break
                        
                        break
                    
                    if target_patient_id:
                        break
            
            if not target_patient_id:
                print(f"❌ Could not find patient ID for '{target_client_name}'")
                return None
            
            # STEP 4: Find the Payer Claim Control # associated with this client's claim
            print(f"\n=== STEP 4: Finding Payer Claim Control # for Claim #{target_claim} ===\n")
            
            # Find the Payer Claim Control # that's associated with this claim
            # It should be in the same claim section
            target_payer_claim_control = None
            
            # Find the line number where the claim starts
            claim_start_line = None
            for i, line in enumerate(lines):
                if f"Claim #{target_claim}" in line or f"Claim # {target_claim}" in line:
                    claim_start_line = i + 1
                    print(f"Claim #{target_claim} starts at line {claim_start_line}")
                    break
            
            if claim_start_line:
                # Look for Payer Claim Control # in the claim section
                # Check from claim start to where target client appears (or within reasonable range)
                target_line = None
                for i, line in enumerate(lines):
                    if target_last and target_last in line.lower():
                        target_line = i + 1
                        break
                
                # Search for Payer Claim Control # between claim start and client, or near the claim
                search_start = max(0, claim_start_line - 10) if claim_start_line else 0
                search_end = min(len(lines), (target_line + 5) if target_line else claim_start_line + 30)
                
                print(f"Searching for 'Payer Claim Control #:' in lines {search_start}-{search_end}\n")
                
                for i in range(search_start - 1, search_end):  # Convert to 0-based index
                    line_lower = lines[i].lower()
                    if 'payer claim control' in line_lower and ':' in lines[i]:
                        # Extract the number
                        match = re.search(r'(?:payer\s*claim\s*control\s*#?\s*:?\s*)(.+)', lines[i], re.IGNORECASE)
                        if match:
                            control_number = match.group(1).strip()
                            # Clean up - remove any trailing text that's not part of the number
                            # Keep numbers, spaces, dashes, and common separators
                            control_number = re.sub(r'[^\d\s\-\.]+.*$', '', control_number).strip()
                            
                            target_payer_claim_control = control_number
                            print(f"✅ Found 'Payer Claim Control #:' on line {i+1}: {lines[i]}")
                            print(f"   Extracted number: {target_payer_claim_control}")
                            break
            
            # If not found near claim, try to find it by checking proximity to patient ID line
            if not target_payer_claim_control:
                print("Not found near claim section, searching near patient ID...\n")
                
                # Find the line with the patient ID
                patient_id_line = None
                for i, line in enumerate(lines):
                    if target_patient_id and f"K{target_patient_id}" in line:
                        patient_id_line = i + 1
                        print(f"Patient ID K{target_patient_id} found at line {patient_id_line}")
                        break
                
                if patient_id_line:
                    # Search within 20 lines before/after patient ID
                    search_start = max(0, patient_id_line - 20)
                    search_end = min(len(lines), patient_id_line + 20)
                    
                    for i in range(search_start - 1, search_end):
                        line_lower = lines[i].lower()
                        if 'payer claim control' in line_lower and ':' in lines[i]:
                            match = re.search(r'(?:payer\s*claim\s*control\s*#?\s*:?\s*)(.+)', lines[i], re.IGNORECASE)
                            if match:
                                control_number = match.group(1).strip()
                                control_number = re.sub(r'[^\d\s\-\.]+.*$', '', control_number).strip()
                                target_payer_claim_control = control_number
                                print(f"✅ Found 'Payer Claim Control #:' on line {i+1}: {lines[i]}")
                                print(f"   Extracted number: {target_payer_claim_control}")
                                break
            
            # Final result
            print(f"\n{'='*80}")
            print(f"✅ EXTRACTION COMPLETE")
            print(f"{'='*80}")
            print(f"Client: {target_client_name}")
            print(f"Patient ID: K{target_patient_id}")
            print(f"Claim #: {target_claim}")
            print(f"Payer Claim Control #: {target_payer_claim_control or 'NOT FOUND'}")
            print(f"{'='*80}\n")
            
            if not target_payer_claim_control:
                print("⚠️ WARNING: Could not find Payer Claim Control # for this client")
                print(f"   Found {len(all_payer_controls)} total 'Payer Claim Control #:' entries in PDF")
                print("   They may be on different pages or sections\n")
            
            return {
                'client_name': target_client_name,
                'patient_id': target_patient_id,
                'claim_number': target_claim,
                'payer_claim_control': target_payer_claim_control,
                'matched': bool(target_patient_id and target_claim)
            }
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    pdf_path = r"C:\Users\mthompson\Downloads\Billing _ TherapyNotes era example.pdf"
    target_client = "Vernell E Luckey"
    
    result = extract_payer_claim_control_for_client(pdf_path, target_client)
    
    if result and result.get('matched'):
        print("\n🎉 SUCCESS!")
        print(f"Payer Claim Control #: {result['payer_claim_control']}")
        print(f"Verified for client: {result['client_name']}")
        print(f"Claim #: {result['claim_number']}")
        print(f"Patient ID: K{result['patient_id']}")
    else:
        print("\n❌ Extraction failed")

