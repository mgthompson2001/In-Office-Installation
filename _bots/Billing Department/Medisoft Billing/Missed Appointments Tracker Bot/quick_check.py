"""Quick check to see if names are matching"""

import pandas as pd
from pathlib import Path

output_excel_path = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\The stuff\Final Merged - Complete (Active Only).xlsx")
master_list_path = Path(r"G:\Company\Master Counselor\Master Counselor List.xlsx")

# Get counselors from output
df_output = pd.read_excel(output_excel_path, sheet_name='Missed Appointments')
output_counselors = set()
for idx, row in df_output.iterrows():
    client_name = str(row.get('Client Name', '')).strip() if pd.notna(row.get('Client Name')) else ''
    if client_name.startswith('COUNSELOR:'):
        counselor_name = client_name.replace('COUNSELOR:', '').strip()
        if counselor_name:
            output_counselors.add(counselor_name)

# Get active counselors from master
df_master = pd.read_excel(master_list_path)
master_counselors = set()
for idx, row in df_master.iterrows():
    last_name = str(row.get('Last Name', '')).strip() if pd.notna(row.get('Last Name')) else ''
    first_name = str(row.get('First Name', '')).strip() if pd.notna(row.get('First Name')) else ''
    notes = str(row.get('Notes', '')).lower() if pd.notna(row.get('Notes')) else ''
    
    if last_name and first_name and 'loa' not in notes and 'resigned' not in notes:
        full_name = f"{last_name}, {first_name}"
        master_counselors.add(full_name)

# Check specific names
test_names = ["Agenor, Monde", "Alam, Sumera F.", "Alcaide, Melissa"]

print("Checking if these names are in both sets:")
for name in test_names:
    in_output = name in output_counselors
    in_master = name in master_counselors
    print(f"  {name}:")
    print(f"    In output: {in_output}")
    print(f"    In master: {in_master}")
    print(f"    Match: {in_output and in_master}")

# Check intersection
exact_matches = output_counselors & master_counselors
print(f"\nExact matches (same string): {len(exact_matches)}")
print(f"Output counselors: {len(output_counselors)}")
print(f"Master counselors: {len(master_counselors)}")

# Show first 10 exact matches
print(f"\nFirst 10 exact matches:")
for i, name in enumerate(sorted(exact_matches)[:10], 1):
    print(f"  {i}. {name}")

