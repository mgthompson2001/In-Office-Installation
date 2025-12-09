"""Debug script to see actual name formats in both files"""

import pandas as pd
from pathlib import Path

output_excel_path = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Final Merged - Complete (Active Only).xlsx")
master_list_path = Path(r"G:\Company\Master Counselor\Master Counselor List.xlsx")

# Read a few rows from output
print("=== OUTPUT EXCEL (First 10 counselors) ===")
df_output = pd.read_excel(output_excel_path, sheet_name='Missed Appointments')
counselors_output = set()
for idx, row in df_output.iterrows():
    client_name = str(row.get('Client Name', '')).strip() if pd.notna(row.get('Client Name')) else ''
    if client_name.startswith('COUNSELOR:'):
        counselor_name = client_name.replace('COUNSELOR:', '').strip()
        if counselor_name and len(counselors_output) < 10:
            counselors_output.add(counselor_name)
            print(f"  {counselor_name}")

print(f"\n=== MASTER LIST (First 10 active counselors) ===")
df_master = pd.read_excel(master_list_path)
count = 0
for idx, row in df_master.iterrows():
    last_name = str(row.get('Last Name', '')).strip() if pd.notna(row.get('Last Name')) else ''
    first_name = str(row.get('First Name', '')).strip() if pd.notna(row.get('First Name')) else ''
    notes = str(row.get('Notes', '')).lower() if pd.notna(row.get('Notes')) else ''
    
    if last_name and first_name and 'loa' not in notes and 'resigned' not in notes:
        full_name = f"{last_name}, {first_name}"
        if count < 10:
            print(f"  {full_name}")
            count += 1

# Check specific names
print(f"\n=== CHECKING SPECIFIC NAMES ===")
test_names = ["Agenor, Monde", "Alam, Sumera F.", "Alcaide, Melissa", "Alers, Alexander"]

for test_name in test_names:
    print(f"\nLooking for: {test_name}")
    
    # In output
    found_in_output = False
    for idx, row in df_output.iterrows():
        client_name = str(row.get('Client Name', '')).strip() if pd.notna(row.get('Client Name')) else ''
        counselor_name = str(row.get('Counselor Name', '')).strip() if pd.notna(row.get('Counselor Name')) else ''
        
        if client_name.startswith('COUNSELOR:'):
            cn = client_name.replace('COUNSELOR:', '').strip()
            if test_name.lower() in cn.lower() or cn.lower() in test_name.lower():
                print(f"  Found in OUTPUT: {cn}")
                found_in_output = True
        elif counselor_name and test_name.lower() in counselor_name.lower():
            print(f"  Found in OUTPUT (Counselor Name col): {counselor_name}")
            found_in_output = True
    
    if not found_in_output:
        print(f"  NOT found in OUTPUT")
    
    # In master
    found_in_master = False
    for idx, row in df_master.iterrows():
        last_name = str(row.get('Last Name', '')).strip() if pd.notna(row.get('Last Name')) else ''
        first_name = str(row.get('First Name', '')).strip() if pd.notna(row.get('First Name')) else ''
        
        if last_name and first_name:
            full_name = f"{last_name}, {first_name}"
            if test_name.lower() in full_name.lower() or full_name.lower() in test_name.lower():
                print(f"  Found in MASTER: {full_name}")
                found_in_master = True
    
    if not found_in_master:
        print(f"  NOT found in MASTER")

