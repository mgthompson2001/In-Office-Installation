import pandas as pd
import sys
import re

# Set encoding to handle special characters
sys.stdout.reconfigure(encoding='utf-8')

def normalize_counselor_name(name):
    """Normalize counselor name to 'first last' format for comparison"""
    if pd.isna(name) or name == '' or str(name).lower() == 'nan':
        return None
    
    name_str = str(name).strip()
    
    # Remove "COUNSELOR:" prefix if present
    name_str = re.sub(r'^counselor:\s*', '', name_str, flags=re.IGNORECASE)
    name_str = name_str.strip()
    
    # Handle "Last, First" format
    if ',' in name_str:
        parts = [p.strip() for p in name_str.split(',')]
        if len(parts) >= 2:
            # Reverse to "First Last"
            name_str = ' '.join(reversed(parts))
    
    # Normalize whitespace and convert to lowercase
    name_str = ' '.join(name_str.split()).lower()
    return name_str

# File paths
master_file = r"G:\Company\Master Counselor\Master Counselor List.xlsx"
output_file1 = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\November Missed Appointment tracker part 1.xlsx"
output_file2 = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Nov Missed Part 2.xlsx"
output_file3 = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Log for remaining Run\Part 3 (Rows 109 through End)\part 3.xlsx"

print("=" * 80)
print("COUNSELOR DATA ANALYSIS")
print("=" * 80)

# Read Master Counselor List
print("\n1. Reading Master Counselor List...")
try:
    master_df = pd.read_excel(master_file)
    print(f"   ✓ Master file loaded: {len(master_df)} rows, {len(master_df.columns)} columns")
    print(f"   Columns: {list(master_df.columns)[:5]}...")
    
    # Create counselor name combinations from master list
    if 'First Name' in master_df.columns and 'Last Name' in master_df.columns:
        master_df['Counselor_Name'] = master_df['First Name'].astype(str).str.strip() + ' ' + master_df['Last Name'].astype(str).str.strip()
        master_counselors_raw = master_df['Counselor_Name'].apply(normalize_counselor_name)
        master_counselors = {c for c in master_counselors_raw if c is not None}
        print(f"   ✓ Found {len(master_counselors)} unique counselors in master list")
    else:
        print("   ✗ ERROR: Could not find 'First Name' and 'Last Name' columns")
        print(f"   Available columns: {list(master_df.columns)}")
        master_counselors = set()
except Exception as e:
    print(f"   ✗ ERROR reading master file: {e}")
    master_counselors = set()
    master_df = pd.DataFrame()

# Read Output File 1
print("\n2. Reading Output File 1 (Part 1)...")
try:
    df1 = pd.read_excel(output_file1)
    print(f"   ✓ File 1 loaded: {len(df1)} rows, {len(df1.columns)} columns")
    print(f"   Columns: {list(df1.columns)[:5]}...")
    
    # Try to find counselor name column (prioritize "Counselor Name")
    counselor_col1 = None
    # First check for exact "Counselor Name" match
    if 'Counselor Name' in df1.columns:
        counselor_col1 = 'Counselor Name'
    else:
        # Then check for columns containing "counselor" (but not "client")
        for col in df1.columns:
            if 'counselor' in col.lower() and 'client' not in col.lower():
                counselor_col1 = col
                break
        # If still not found, check for any name column
        if not counselor_col1:
            for col in df1.columns:
                if 'name' in col.lower():
                    counselor_col1 = col
                    break
    
    if counselor_col1:
        counselors1_raw = df1[counselor_col1].apply(normalize_counselor_name)
        counselors1 = {c for c in counselors1_raw if c is not None}
        print(f"   ✓ Found counselor column: '{counselor_col1}'")
        print(f"   ✓ Found {len(counselors1)} unique counselors in Part 1")
    else:
        print(f"   ⚠ Could not identify counselor column. Available columns: {list(df1.columns)}")
        counselors1 = set()
except Exception as e:
    print(f"   ✗ ERROR reading file 1: {e}")
    counselors1 = set()
    df1 = pd.DataFrame()

# Read Output File 2
print("\n3. Reading Output File 2 (Part 2)...")
try:
    df2 = pd.read_excel(output_file2)
    print(f"   ✓ File 2 loaded: {len(df2)} rows, {len(df2.columns)} columns")
    print(f"   Columns: {list(df2.columns)[:5]}...")
    
    # Try to find counselor name column (prioritize "Counselor Name")
    counselor_col2 = None
    # First check for exact "Counselor Name" match
    if 'Counselor Name' in df2.columns:
        counselor_col2 = 'Counselor Name'
    else:
        # Then check for columns containing "counselor" (but not "client")
        for col in df2.columns:
            if 'counselor' in col.lower() and 'client' not in col.lower():
                counselor_col2 = col
                break
        # If still not found, check for any name column
        if not counselor_col2:
            for col in df2.columns:
                if 'name' in col.lower():
                    counselor_col2 = col
                    break
    
    if counselor_col2:
        counselors2_raw = df2[counselor_col2].apply(normalize_counselor_name)
        counselors2 = {c for c in counselors2_raw if c is not None}
        print(f"   ✓ Found counselor column: '{counselor_col2}'")
        print(f"   ✓ Found {len(counselors2)} unique counselors in Part 2")
    else:
        print(f"   ⚠ Could not identify counselor column. Available columns: {list(df2.columns)}")
        counselors2 = set()
except Exception as e:
    print(f"   ✗ ERROR reading file 2: {e}")
    counselors2 = set()
    df2 = pd.DataFrame()

# Read Output File 3
print("\n4. Reading Output File 3 (Part 3)...")
try:
    df3 = pd.read_excel(output_file3)
    print(f"   ✓ File 3 loaded: {len(df3)} rows, {len(df3.columns)} columns")
    print(f"   Columns: {list(df3.columns)[:5]}...")
    
    # Try to find counselor name column (prioritize "Counselor Name")
    counselor_col3 = None
    # First check for exact "Counselor Name" match
    if 'Counselor Name' in df3.columns:
        counselor_col3 = 'Counselor Name'
    else:
        # Then check for columns containing "counselor" (but not "client")
        for col in df3.columns:
            if 'counselor' in col.lower() and 'client' not in col.lower():
                counselor_col3 = col
                break
        # If still not found, check for any name column
        if not counselor_col3:
            for col in df3.columns:
                if 'name' in col.lower():
                    counselor_col3 = col
                    break
    
    if counselor_col3:
        counselors3_raw = df3[counselor_col3].apply(normalize_counselor_name)
        counselors3 = {c for c in counselors3_raw if c is not None}
        print(f"   ✓ Found counselor column: '{counselor_col3}'")
        print(f"   ✓ Found {len(counselors3)} unique counselors in Part 3")
    else:
        print(f"   ⚠ Could not identify counselor column. Available columns: {list(df3.columns)}")
        counselors3 = set()
except Exception as e:
    print(f"   ✗ ERROR reading file 3: {e}")
    counselors3 = set()
    df3 = pd.DataFrame()

# Analysis
print("\n" + "=" * 80)
print("ANALYSIS RESULTS")
print("=" * 80)

# Total unique counselors across all output files
all_output_counselors = counselors1 | counselors2 | counselors3
print(f"\n📊 COUNSELOR COUNTS:")
print(f"   • Part 1: {len(counselors1)} unique counselors")
print(f"   • Part 2: {len(counselors2)} unique counselors")
print(f"   • Part 3: {len(counselors3)} unique counselors")
print(f"   • TOTAL across all output files: {len(all_output_counselors)} unique counselors")
print(f"   • Master List: {len(master_counselors)} unique counselors")

# Check overlaps between output files
print(f"\n🔄 OVERLAP ANALYSIS BETWEEN OUTPUT FILES:")
overlap_12 = counselors1 & counselors2
overlap_13 = counselors1 & counselors3
overlap_23 = counselors2 & counselors3
overlap_all = counselors1 & counselors2 & counselors3

print(f"   • Overlap between Part 1 & Part 2: {len(overlap_12)} counselors")
if overlap_12:
    overlap_list = sorted(list(overlap_12))
    print(f"     Names: {overlap_list[:10]}")
    if len(overlap_list) > 10:
        print(f"     ... and {len(overlap_list) - 10} more")

print(f"   • Overlap between Part 1 & Part 3: {len(overlap_13)} counselors")
if overlap_13:
    overlap_list = sorted(list(overlap_13))
    print(f"     Names: {overlap_list[:10]}")
    if len(overlap_list) > 10:
        print(f"     ... and {len(overlap_list) - 10} more")

print(f"   • Overlap between Part 2 & Part 3: {len(overlap_23)} counselors")
if overlap_23:
    overlap_list = sorted(list(overlap_23))
    print(f"     Names: {overlap_list[:10]}")
    if len(overlap_list) > 10:
        print(f"     ... and {len(overlap_list) - 10} more")

print(f"   • Overlap in ALL THREE files: {len(overlap_all)} counselors")
if overlap_all:
    print(f"     Names: {sorted(list(overlap_all))}")

# Compare with master list
print(f"\n📋 COMPARISON WITH MASTER LIST:")
if master_counselors:
    in_master = all_output_counselors & master_counselors
    not_in_master = all_output_counselors - master_counselors
    in_master_not_in_output = master_counselors - all_output_counselors
    
    print(f"   • Output counselors found in Master List: {len(in_master)}/{len(all_output_counselors)}")
    print(f"   • Output counselors NOT in Master List: {len(not_in_master)}")
    if not_in_master:
        not_in_master_list = sorted(list(not_in_master))
        print(f"     Names: {not_in_master_list[:20]}")
        if len(not_in_master_list) > 20:
            print(f"     ... and {len(not_in_master_list) - 20} more")
    
    print(f"   • Master List counselors NOT in output files: {len(in_master_not_in_output)}")
    if len(in_master_not_in_output) > 0 and len(in_master_not_in_output) <= 50:
        print(f"     Names: {sorted(list(in_master_not_in_output))}")
    elif len(in_master_not_in_output) > 50:
        print(f"     (Showing first 50 of {len(in_master_not_in_output)}):")
        print(f"     Names: {sorted(list(in_master_not_in_output))[:50]}")

# Show sample data from each file
print(f"\n📄 SAMPLE DATA:")
if not df1.empty and counselor_col1:
    print(f"\n   Part 1 - First 5 counselor names:")
    for idx, name in enumerate(df1[counselor_col1].head(5), 1):
        print(f"     {idx}. {name}")

if not df2.empty and counselor_col2:
    print(f"\n   Part 2 - First 5 counselor names:")
    for idx, name in enumerate(df2[counselor_col2].head(5), 1):
        print(f"     {idx}. {name}")

if not df3.empty and counselor_col3:
    print(f"\n   Part 3 - First 5 counselor names:")
    for idx, name in enumerate(df3[counselor_col3].head(5), 1):
        print(f"     {idx}. {name}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)

