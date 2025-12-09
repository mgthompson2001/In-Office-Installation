import pandas as pd
import sys
import re
from datetime import datetime

# Set encoding to handle special characters
sys.stdout.reconfigure(encoding='utf-8')

# File paths
master_file = r"G:\Company\Master Counselor\Master Counselor List.xlsx"
output_file1 = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\November Missed Appointment tracker part 1.xlsx"
output_file2 = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Nov Missed Part 2.xlsx"
output_file3 = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Log for remaining Run\Part 3 (Rows 109 through End)\part 3.xlsx"
output_report = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Missing Counselors Report.xlsx"

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

print("=" * 80)
print("GENERATING MISSING COUNSELORS REPORT")
print("=" * 80)

# Read Master Counselor List
print("\n1. Reading Master Counselor List...")
master_df = pd.read_excel(master_file)
print(f"   ✓ Master file loaded: {len(master_df)} rows")

# Filter out invalid rows (notes, instructions, etc.)
# Remove rows where First Name or Last Name is NaN, empty, or contains common note keywords
invalid_keywords = ['key', 'blue', 'green', 'orange', 'purple', 'red', 'white', 'yellow', 
                    'gray', 'bold', 'counselors must', 'supervision', 'mail', 'check']
master_df = master_df[
    master_df['First Name'].notna() & 
    master_df['Last Name'].notna() &
    (master_df['First Name'].astype(str).str.strip() != 'nan') &
    (master_df['Last Name'].astype(str).str.strip() != 'nan') &
    (master_df['First Name'].astype(str).str.strip() != '') &
    (master_df['Last Name'].astype(str).str.strip() != '')
].copy()

# Further filter: remove rows where name contains invalid keywords
name_combined = (master_df['First Name'].astype(str).str.lower() + ' ' + 
                 master_df['Last Name'].astype(str).str.lower())
is_valid = ~name_combined.str.contains('|'.join(invalid_keywords), case=False, na=False)
master_df = master_df[is_valid].copy()

print(f"   ✓ After filtering invalid entries: {len(master_df)} valid counselors")

# Create normalized names for master list
master_df['Normalized_Name'] = (master_df['First Name'].astype(str).str.strip() + ' ' + 
                                 master_df['Last Name'].astype(str).str.strip()).str.lower()
master_df['Normalized_Name'] = master_df['Normalized_Name'].str.strip()

# Read all output files and collect counselor names
print("\n2. Reading output files and collecting counselor names...")

all_output_counselors = set()

# File 1
df1 = pd.read_excel(output_file1)
if 'Counselor Name' in df1.columns:
    counselors1_raw = df1['Counselor Name'].apply(normalize_counselor_name)
    counselors1 = {c for c in counselors1_raw if c is not None}
    all_output_counselors.update(counselors1)
    print(f"   ✓ Part 1: {len(counselors1)} unique counselors")

# File 2
df2 = pd.read_excel(output_file2)
if 'Counselor Name' in df2.columns:
    counselors2_raw = df2['Counselor Name'].apply(normalize_counselor_name)
    counselors2 = {c for c in counselors2_raw if c is not None}
    all_output_counselors.update(counselors2)
    print(f"   ✓ Part 2: {len(counselors2)} unique counselors")

# File 3
df3 = pd.read_excel(output_file3)
if 'Counselor Name' in df3.columns:
    counselors3_raw = df3['Counselor Name'].apply(normalize_counselor_name)
    counselors3 = {c for c in counselors3_raw if c is not None}
    all_output_counselors.update(counselors3)
    print(f"   ✓ Part 3: {len(counselors3)} unique counselors")

print(f"   ✓ Total unique counselors in output files: {len(all_output_counselors)}")

# Find missing counselors
print("\n3. Identifying missing counselors...")
master_normalized = set(master_df['Normalized_Name'].str.lower().str.strip())
missing_normalized = master_normalized - all_output_counselors

# Filter out invalid entries (like "nan", empty strings, or notes)
missing_normalized = {m for m in missing_normalized if m and m != 'nan' and len(m) > 2}

# Get full records for missing counselors
missing_counselors_df = master_df[master_df['Normalized_Name'].str.lower().str.strip().isin(missing_normalized)].copy()

# Sort by Last Name, then First Name
missing_counselors_df = missing_counselors_df.sort_values(['Last Name', 'First Name'])

print(f"   ✓ Found {len(missing_counselors_df)} missing counselors")

# Generate detailed report
print("\n4. Generating detailed report...")

report_lines = []
report_lines.append("=" * 80)
report_lines.append("MISSING COUNSELORS REPORT")
report_lines.append("=" * 80)
report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
report_lines.append("")
report_lines.append(f"Total counselors in Master List: {len(master_df)}")
report_lines.append(f"Total counselors in output files: {len(all_output_counselors)}")
report_lines.append(f"Missing counselors: {len(missing_counselors_df)}")
report_lines.append("")
report_lines.append("=" * 80)
report_lines.append("DETAILED LIST OF MISSING COUNSELORS")
report_lines.append("=" * 80)
report_lines.append("")

for num, (idx, row) in enumerate(missing_counselors_df.iterrows(), 1):
    report_lines.append(f"{num}. {row['First Name']} {row['Last Name']}")
    if pd.notna(row.get('Email')):
        report_lines.append(f"   Email: {row['Email']}")
    if pd.notna(row.get('Program? (In-Home, Telehealth, FUH, Sup, IA Only)')):
        report_lines.append(f"   Program: {row['Program? (In-Home, Telehealth, FUH, Sup, IA Only)']}")
    if pd.notna(row.get('Date of Term')):
        report_lines.append(f"   Date of Term: {row['Date of Term']}")
    report_lines.append("")

# Print report to console
print("\n" + "\n".join(report_lines))

# Save report to text file
report_text_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Missing Counselors Report.txt"
with open(report_text_file, 'w', encoding='utf-8') as f:
    f.write("\n".join(report_lines))
print(f"\n   ✓ Text report saved to: {report_text_file}")

# Create Excel file with missing counselors
print("\n5. Creating Excel file with missing counselors...")

# Select relevant columns for the Excel output
excel_columns = [
    'First Name', 
    'Last Name', 
    'Email',
    'Program? (In-Home, Telehealth, FUH, Sup, IA Only)',
    'date of hire',
    'Date of Term',
    'Phone #',
    'Sup',
    'Lic #',
    'NPI'
]

# Only include columns that exist in the dataframe
available_columns = [col for col in excel_columns if col in missing_counselors_df.columns]
missing_counselors_excel = missing_counselors_df[available_columns].copy()

# Add a status column
missing_counselors_excel.insert(0, 'Status', 'MISSING FROM OUTPUT FILES')

# Save to Excel
with pd.ExcelWriter(output_report, engine='openpyxl') as writer:
    missing_counselors_excel.to_excel(writer, sheet_name='Missing Counselors', index=False)
    
    # Auto-adjust column widths
    worksheet = writer.sheets['Missing Counselors']
    from openpyxl.utils import get_column_letter
    for idx, col in enumerate(missing_counselors_excel.columns, 1):
        max_length = max(
            missing_counselors_excel[col].astype(str).map(len).max(),
            len(str(col))
        )
        col_letter = get_column_letter(idx)
        worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)

print(f"   ✓ Excel file saved to: {output_report}")
print(f"   ✓ Excel contains {len(missing_counselors_excel)} missing counselors")

print("\n" + "=" * 80)
print("REPORT GENERATION COMPLETE")
print("=" * 80)
print(f"\nSummary:")
print(f"  • Missing counselors found: {len(missing_counselors_df)}")
print(f"  • Text report: {report_text_file}")
print(f"  • Excel report: {output_report}")

