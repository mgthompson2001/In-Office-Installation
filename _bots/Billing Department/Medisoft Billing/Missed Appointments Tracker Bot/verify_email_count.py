"""
Script to verify that the number of emails being sent matches the expected
number of active counselors from the Master Counselor List (excluding LOA/resigned).
"""

import pandas as pd
from pathlib import Path
import re
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# File paths
output_excel_path = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Final Merged - Complete (Active Only).xlsx")
master_list_path = Path(r"G:\Company\Master Counselor\Master Counselor List.xlsx")

def normalize_name(name):
    """Normalize name for comparison - handles various formats"""
    if pd.isna(name) or not name:
        return ""
    name = str(name).strip().lower()
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name)
    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)
    # Remove extra spaces again
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def extract_name_parts(name):
    """Extract last and first name parts from various formats"""
    if not name or pd.isna(name):
        return None, None
    
    name = str(name).strip()
    
    # Handle "Last, First" format
    if ',' in name:
        parts = [p.strip() for p in name.split(',', 1)]
        if len(parts) == 2:
            return normalize_name(parts[0]), normalize_name(parts[1])
    
    # Handle "First Last" format
    parts = name.split()
    if len(parts) >= 2:
        # Last name is typically the last word, first name is the first word(s)
        last = normalize_name(parts[-1])
        first = normalize_name(' '.join(parts[:-1]))
        return last, first
    
    return None, None

def names_match(name1, name2):
    """Check if two names match using multiple strategies"""
    # First try exact normalized match
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    
    if norm1 == norm2:
        return True
    
    # Also try without removing punctuation (periods in middle initials)
    norm1_keep_punct = str(name1).strip().lower()
    norm1_keep_punct = re.sub(r'\s+', ' ', norm1_keep_punct)
    norm2_keep_punct = str(name2).strip().lower()
    norm2_keep_punct = re.sub(r'\s+', ' ', norm2_keep_punct)
    
    if norm1_keep_punct == norm2_keep_punct:
        return True
    
    # Extract name parts for fuzzy matching
    last1, first1 = extract_name_parts(name1)
    last2, first2 = extract_name_parts(name2)
    
    if not last1 or not last2:
        return False
    
    # Match if last name matches exactly
    if last1 == last2:
        # Get first word of first name (ignore middle initials/names)
        first1_parts = first1.split() if first1 else []
        first2_parts = first2.split() if first2 else []
        
        if first1_parts and first2_parts:
            # Match if first name word matches (case-insensitive)
            if first1_parts[0].lower() == first2_parts[0].lower():
                return True
            # Match if first initial matches
            if len(first1_parts[0]) > 0 and len(first2_parts[0]) > 0:
                if first1_parts[0][0].lower() == first2_parts[0][0].lower():
                    return True
    
    return False

def is_loa_or_resigned(row, notes_col='Notes', date_of_term_col='Date of Term'):
    """Check if counselor is on LOA or resigned"""
    # Check Notes column for LOA/resigned keywords
    notes = str(row.get(notes_col, '')).lower() if pd.notna(row.get(notes_col)) else ''
    
    loa_keywords = ['loa', 'leave of absence', 'on leave']
    resigned_keywords = ['resigned', 'resigning', 'resignation', 'will be resigning']
    
    # Exclusions (these should NOT be considered LOA/resigned)
    loa_exclusions = ['returned from loa', 'back from loa']
    resigned_exclusions = ['rescinded resignation']
    
    # Check for exclusions first
    for exclusion in loa_exclusions + resigned_exclusions:
        if exclusion in notes:
            return False
    
    # Check for LOA
    for keyword in loa_keywords:
        if keyword in notes:
            return True
    
    # Check for resigned
    for keyword in resigned_keywords:
        if keyword in notes:
            return True
    
    # Check Date of Term column
    date_of_term = row.get(date_of_term_col)
    if pd.notna(date_of_term) and str(date_of_term).strip():
        # If there's a termination date, consider them resigned
        return True
    
    # Check cell color (red fill indicates resigned)
    # Note: This requires openpyxl, but we'll skip for now as it's complex
    
    return False

def is_key_row(row):
    """Check if this is a KEY/instruction row, not an actual counselor"""
    last_name = str(row.get('Last Name', '')).lower() if pd.notna(row.get('Last Name')) else ''
    first_name = str(row.get('First Name', '')).lower() if pd.notna(row.get('First Name')) else ''
    notes = str(row.get('Notes', '')).lower() if pd.notna(row.get('Notes')) else ''
    
    key_indicators = [
        'key', 'all counselors', 'minimum', 'cases', 'must have',
        'nan', 'none', 'n/a', 'na'
    ]
    
    # Check if name fields contain key indicators
    for indicator in key_indicators:
        if indicator in last_name or indicator in first_name:
            return True
    
    # Check if notes contain instructions
    if 'all counselors' in notes or 'minimum' in notes.lower():
        return True
    
    return False

def get_active_counselors_from_master():
    """Get list of active counselors from Master Counselor List"""
    print(f"Reading Master Counselor List from: {master_list_path}")
    
    if not master_list_path.exists():
        print(f"ERROR: Master Counselor List not found at: {master_list_path}")
        return set(), {}
    
    try:
        # Read the Excel file
        df = pd.read_excel(master_list_path)
        
        print(f"   Total rows in Master List: {len(df)}")
        
        # Get column names (case-insensitive matching)
        last_name_col = None
        first_name_col = None
        notes_col = None
        date_of_term_col = None
        email_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'last name' in col_lower or 'lastname' in col_lower:
                last_name_col = col
            elif 'first name' in col_lower or 'firstname' in col_lower:
                first_name_col = col
            elif 'notes' in col_lower:
                notes_col = col
            elif 'date of term' in col_lower or 'termination' in col_lower:
                date_of_term_col = col
            elif 'email' in col_lower:
                email_col = col
        
        if not last_name_col or not first_name_col:
            print(f"ERROR: Could not find Last Name or First Name columns")
            print(f"   Available columns: {list(df.columns)}")
            return set(), {}
        
        print(f"   Using columns: Last Name='{last_name_col}', First Name='{first_name_col}'")
        if notes_col:
            print(f"   Notes column: '{notes_col}'")
        if date_of_term_col:
            print(f"   Date of Term column: '{date_of_term_col}'")
        
        active_counselors = set()
        counselor_info = {}
        loa_count = 0
        resigned_count = 0
        key_row_count = 0
        empty_name_count = 0
        
        for idx, row in df.iterrows():
            last_name = str(row.get(last_name_col, '')).strip() if pd.notna(row.get(last_name_col)) else ''
            first_name = str(row.get(first_name_col, '')).strip() if pd.notna(row.get(first_name_col)) else ''
            
            # Skip empty names
            if not last_name and not first_name:
                empty_name_count += 1
                continue
            
            # Skip KEY rows
            if is_key_row(row):
                key_row_count += 1
                continue
            
            # Skip if name contains "IPS" (these are program types, not counselors)
            if 'ips' in last_name.lower() or 'ips' in first_name.lower():
                continue
            
            # Check if LOA or resigned - but be more lenient, only exclude if clearly marked
            # Don't exclude based on cell colors or ambiguous notes
            notes_lower = str(row.get(notes_col, '')).lower() if pd.notna(row.get(notes_col)) else ''
            date_of_term = row.get(date_of_term_col)
            
            # Only exclude if explicitly marked as LOA/resigned in notes OR has termination date
            is_excluded = False
            if date_of_term_col and pd.notna(date_of_term) and str(date_of_term).strip():
                # Has termination date - exclude
                is_excluded = True
                resigned_count += 1
            elif 'loa' in notes_lower and 'returned from loa' not in notes_lower and 'back from loa' not in notes_lower:
                is_excluded = True
                loa_count += 1
            elif any(kw in notes_lower for kw in ['resigned', 'resigning', 'resignation']) and 'rescinded resignation' not in notes_lower:
                is_excluded = True
                resigned_count += 1
            
            if is_excluded:
                continue
            
            # This is an active counselor
            full_name = f"{last_name}, {first_name}".strip(', ')
            # Store the original name for matching
            active_counselors.add(full_name)
            
            # Store info
            email = str(row.get(email_col, '')).strip() if email_col and pd.notna(row.get(email_col)) else ''
            counselor_info[full_name] = {
                'full_name': full_name,
                'email': email,
                'last_name': last_name,
                'first_name': first_name
            }
        
        print(f"\nMaster List Analysis:")
        print(f"   Active counselors: {len(active_counselors)}")
        print(f"   LOA counselors: {loa_count}")
        print(f"   Resigned counselors: {resigned_count}")
        print(f"   KEY/instruction rows skipped: {key_row_count}")
        print(f"   Empty name rows skipped: {empty_name_count}")
        
        return active_counselors, counselor_info
        
    except Exception as e:
        print(f"ERROR reading Master Counselor List: {e}")
        import traceback
        traceback.print_exc()
        return set(), {}

def get_counselors_from_output():
    """Get list of counselors from output Excel"""
    print(f"\nReading Output Excel from: {output_excel_path}")
    
    if not output_excel_path.exists():
        print(f"ERROR: Output Excel not found at: {output_excel_path}")
        return set(), {}
    
    try:
        # Read the Missed Appointments sheet
        df = pd.read_excel(output_excel_path, sheet_name='Missed Appointments')
        
        print(f"   Total rows in Output Excel: {len(df)}")
        
        counselors = set()
        counselor_info = {}
        
        for idx, row in df.iterrows():
            client_name = str(row.get('Client Name', '')).strip() if pd.notna(row.get('Client Name')) else ''
            counselor_name = str(row.get('Counselor Name', '')).strip() if pd.notna(row.get('Counselor Name')) else ''
            
            # Check if this is a counselor header row
            if client_name.startswith('COUNSELOR:'):
                counselor_name_from_header = client_name.replace('COUNSELOR:', '').strip()
                if counselor_name_from_header:
                    counselors.add(counselor_name_from_header)
                    counselor_info[counselor_name_from_header] = {
                        'full_name': counselor_name_from_header,
                        'email': str(row.get('Counselor Email', '')).strip() if pd.notna(row.get('Counselor Email')) else ''
                    }
            # Also check Counselor Name column for client rows
            elif counselor_name and counselor_name not in ['', 'nan', 'None']:
                counselors.add(counselor_name)
                if counselor_name not in counselor_info:
                    counselor_info[counselor_name] = {
                        'full_name': counselor_name,
                        'email': str(row.get('Counselor Email', '')).strip() if pd.notna(row.get('Counselor Email')) else ''
                    }
        
        print(f"\nOutput Excel Analysis:")
        print(f"   Unique counselors found: {len(counselors)}")
        
        return counselors, counselor_info
        
    except Exception as e:
        print(f"ERROR reading Output Excel: {e}")
        import traceback
        traceback.print_exc()
        return set(), {}

def compare_counselors(master_counselors, output_counselors, master_info, output_info):
    """Compare the two lists and report discrepancies using fuzzy matching"""
    print(f"\n{'='*70}")
    print(f"COMPARISON RESULTS")
    print(f"{'='*70}\n")
    
    # First, try exact string matching (simplest and most reliable)
    exact_matches = output_counselors & master_counselors
    unmatched_output = output_counselors - exact_matches
    unmatched_master = master_counselors - exact_matches
    
    # Then try fuzzy matching for remaining
    fuzzy_matched_output = set()
    fuzzy_matched_master = set()
    
    for output_name in list(unmatched_output):
        for master_name in list(unmatched_master):
            if names_match(output_name, master_name):
                fuzzy_matched_output.add(output_name)
                fuzzy_matched_master.add(master_name)
                unmatched_output.remove(output_name)
                unmatched_master.remove(master_name)
                break
    
    # Combine exact and fuzzy matches
    all_matched = exact_matches | fuzzy_matched_master
    matching = all_matched
    missing = unmatched_master
    extra = unmatched_output
    
    print(f"MATCHING counselors: {len(matching)}")
    print(f"MISSING from output (should be sent email): {len(missing)}")
    print(f"EXTRA in output (not in master list): {len(extra)}")
    print(f"\nTotal emails that will be sent: {len(output_counselors)}")
    print(f"Expected active counselors from Master List: {len(master_counselors)}")
    
    if missing:
        print(f"\n*** MISSING COUNSELORS (Not in output, should receive email):")
        print(f"   {'-'*65}")
        missing_list = sorted([master_info.get(name, {}).get('full_name', name) for name in missing])
        for i, name in enumerate(missing_list, 1):
            email = master_info.get(name, {}).get('email', 'N/A')
            print(f"   {i:3d}. {name:50s} Email: {email}")
    
    if extra:
        print(f"\n*** EXTRA COUNSELORS (In output but not in Master List):")
        print(f"   {'-'*65}")
        extra_list = sorted([output_info.get(name, {}).get('full_name', name) for name in extra])
        for i, name in enumerate(extra_list, 1):
            email = output_info.get(name, {}).get('email', 'N/A')
            print(f"   {i:3d}. {name:50s} Email: {email}")
    
    if not missing and not extra:
        print(f"\n*** PERFECT MATCH! All active counselors from Master List are in the output.")
        print(f"   The count of {len(output_counselors)} emails is correct.")
    else:
        print(f"\n*** DISCREPANCY DETECTED!")
        if missing:
            print(f"   - {len(missing)} active counselor(s) are missing from the output")
        if extra:
            print(f"   - {len(extra)} counselor(s) in output are not in the Master List")
    
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    print("="*70)
    print("EMAIL COUNT VERIFICATION")
    print("="*70)
    print()
    
    # Get active counselors from Master List
    master_counselors, master_info = get_active_counselors_from_master()
    
    # Get counselors from output Excel
    output_counselors, output_info = get_counselors_from_output()
    
    # Compare
    if master_counselors and output_counselors:
        compare_counselors(master_counselors, output_counselors, master_info, output_info)
    else:
        print("\nERROR: Could not complete comparison due to errors above.")

