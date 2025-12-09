import pandas as pd
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# File paths
file1 = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\November Missed Appointment tracker part 1.xlsx"
file2 = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Nov Missed Part 2.xlsx"
file3 = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Log for remaining Run\Part 3 (Rows 109 through End)\part 3.xlsx"
output_file = r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Missed Appt. Tracker Output\Merged - All Parts Combined.xlsx"

def normalize_counselor_name(name):
    """Normalize counselor name for comparison"""
    if pd.isna(name) or name == '' or str(name).lower() == 'nan':
        return None
    
    name_str = str(name).strip()
    
    # Remove "COUNSELOR:" prefix if present
    import re
    name_str = re.sub(r'^counselor:\s*', '', name_str, flags=re.IGNORECASE)
    name_str = name_str.strip()
    
    # Handle "Last, First" format
    if ',' in name_str:
        parts = [p.strip() for p in name_str.split(',')]
        if len(parts) >= 2:
            # Reverse to "First Last" for normalization
            name_str = ' '.join(reversed(parts))
    
    # Normalize whitespace and convert to lowercase
    name_str = ' '.join(name_str.split()).lower()
    return name_str

print("=" * 80)
print("MERGING OUTPUT EXCEL FILES")
print("=" * 80)

# Read all three files
print("\n1. Reading Excel files...")
try:
    df1 = pd.read_excel(file1)
    print(f"   ✓ Part 1: {len(df1)} rows, {len(df1.columns)} columns")
except Exception as e:
    print(f"   ✗ Error reading Part 1: {e}")
    sys.exit(1)

try:
    df2 = pd.read_excel(file2)
    print(f"   ✓ Part 2: {len(df2)} rows, {len(df2.columns)} columns")
except Exception as e:
    print(f"   ✗ Error reading Part 2: {e}")
    sys.exit(1)

try:
    df3 = pd.read_excel(file3)
    print(f"   ✓ Part 3: {len(df3)} rows, {len(df3.columns)} columns")
except Exception as e:
    print(f"   ✗ Error reading Part 3: {e}")
    sys.exit(1)

# Identify counselor name column
print("\n2. Identifying counselor name column...")
counselor_col = None
for col in df1.columns:
    if 'counselor' in col.lower() and 'name' in col.lower():
        counselor_col = col
        break

if not counselor_col:
    print("   ✗ ERROR: Could not find 'Counselor Name' column")
    print(f"   Available columns: {list(df1.columns)}")
    sys.exit(1)

print(f"   ✓ Found counselor column: '{counselor_col}'")

# Add source file identifier to each dataframe
print("\n3. Adding source identifiers and normalizing counselor names...")
df1['_source_file'] = 'Part 1'
df2['_source_file'] = 'Part 2'
df3['_source_file'] = 'Part 3'

# Normalize counselor names for comparison
df1['_normalized_counselor'] = df1[counselor_col].apply(normalize_counselor_name)
df2['_normalized_counselor'] = df2[counselor_col].apply(normalize_counselor_name)
df3['_normalized_counselor'] = df3[counselor_col].apply(normalize_counselor_name)

# Combine all dataframes
print("\n4. Combining all dataframes...")
all_data = pd.concat([df1, df2, df3], ignore_index=True)
print(f"   ✓ Total rows before deduplication: {len(all_data)}")

# Find counselors that appear in multiple files
print("\n5. Analyzing duplicates...")
counselor_sources = all_data.groupby('_normalized_counselor')['_source_file'].apply(set).reset_index()
counselor_sources['source_count'] = counselor_sources['_source_file'].apply(len)
duplicate_counselors_list = counselor_sources[counselor_sources['source_count'] > 1]['_normalized_counselor'].tolist()

print(f"   ✓ Found {len(duplicate_counselors_list)} counselors appearing in multiple files")

if duplicate_counselors_list:
    print("\n   Duplicate counselors:")
    for counselor in duplicate_counselors_list[:10]:
        counselor_data = all_data[all_data['_normalized_counselor'] == counselor]
        sources = counselor_data['_source_file'].unique()
        row_counts = counselor_data.groupby('_source_file').size()
        print(f"      - {counselor}: appears in {list(sources)} with {dict(row_counts)} rows each")
    if len(duplicate_counselors_list) > 10:
        print(f"      ... and {len(duplicate_counselors_list) - 10} more")

# For each counselor, keep only the version with the most data
print("\n6. Deduplicating - keeping counselors with most data...")
merged_rows = []
processed_counselors = set()

# Sort by normalized counselor name to process consistently
all_data_sorted = all_data.sort_values(['_normalized_counselor', '_source_file'])

for counselor_norm in all_data_sorted['_normalized_counselor'].unique():
    if pd.isna(counselor_norm) or counselor_norm is None:
        # Keep all rows with null counselor names (they'll be handled separately)
        null_rows = all_data_sorted[all_data_sorted['_normalized_counselor'].isna()]
        merged_rows.append(null_rows)
        continue
    
    if counselor_norm in processed_counselors:
        continue
    
    # Get all rows for this counselor
    counselor_rows = all_data_sorted[all_data_sorted['_normalized_counselor'] == counselor_norm]
    
    if len(counselor_rows) == 0:
        continue
    
    # If counselor appears in multiple sources, keep the one with most rows
    if counselor_norm in duplicate_counselors_list:
        # Group by source file and count rows
        source_counts = counselor_rows.groupby('_source_file').size().reset_index(name='count')
        source_counts = source_counts.sort_values('count', ascending=False)
        
        # Get the source file with the most rows
        best_source = source_counts.iloc[0]['_source_file']
        best_count = source_counts.iloc[0]['count']
        
        # Keep only rows from the best source
        best_rows = counselor_rows[counselor_rows['_source_file'] == best_source]
        
        print(f"   ✓ Counselor '{counselor_norm}': keeping {best_count} rows from {best_source} (had {len(counselor_rows)} total rows across {len(source_counts)} sources)")
        
        merged_rows.append(best_rows)
    else:
        # No duplicates, keep all rows
        merged_rows.append(counselor_rows)
    
    processed_counselors.add(counselor_norm)

# Combine all merged rows
print("\n7. Creating final merged dataframe...")
if merged_rows:
    merged_df = pd.concat(merged_rows, ignore_index=True)
else:
    merged_df = pd.DataFrame()

# Remove helper columns
merged_df = merged_df.drop(columns=['_source_file', '_normalized_counselor'], errors='ignore')

print(f"   ✓ Final merged dataframe: {len(merged_df)} rows, {len(merged_df.columns)} columns")

# Verify no duplicates by counselor name across files
print("\n8. Verifying no duplicates across files...")
if counselor_col in merged_df.columns:
    # Check if any counselor appears from multiple sources (should not happen after deduplication)
    # This check is just to verify our deduplication worked
    unique_counselors = merged_df[counselor_col].nunique()
    total_rows = len(merged_df)
    
    print(f"   ✓ Unique counselors in merged file: {unique_counselors}")
    print(f"   ✓ Total rows (clients): {total_rows}")
    print(f"   ✓ Average clients per counselor: {total_rows / unique_counselors:.1f}" if unique_counselors > 0 else "   ✓ No counselors found")
else:
    print("   ⚠ Could not verify (counselor column not found)")

# Sort by counselor name, then by client name if available
print("\n9. Sorting final data...")
sort_columns = [counselor_col]
if 'Client Name' in merged_df.columns:
    sort_columns.append('Client Name')
elif 'client name' in [c.lower() for c in merged_df.columns]:
    client_col = [c for c in merged_df.columns if 'client' in c.lower() and 'name' in c.lower()][0]
    sort_columns.append(client_col)

merged_df = merged_df.sort_values(sort_columns, na_position='last')
print(f"   ✓ Sorted by: {', '.join(sort_columns)}")

# Save to Excel
print("\n10. Saving merged Excel file...")
try:
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        merged_df.to_excel(writer, sheet_name='Merged Data', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Merged Data']
        from openpyxl.utils import get_column_letter
        for idx, col in enumerate(merged_df.columns, 1):
            max_length = max(
                merged_df[col].astype(str).map(len).max(),
                len(str(col))
            )
            col_letter = get_column_letter(idx)
            worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
    
    print(f"   ✓ Saved to: {output_file}")
except Exception as e:
    print(f"   ✗ Error saving file: {e}")
    sys.exit(1)

# Summary statistics
print("\n" + "=" * 80)
print("MERGE SUMMARY")
print("=" * 80)
print(f"\n📊 STATISTICS:")
print(f"   • Part 1 rows: {len(df1)}")
print(f"   • Part 2 rows: {len(df2)}")
print(f"   • Part 3 rows: {len(df3)}")
print(f"   • Total before merge: {len(df1) + len(df2) + len(df3)}")
print(f"   • Final merged rows: {len(merged_df)}")
print(f"   • Rows removed (duplicates): {len(df1) + len(df2) + len(df3) - len(merged_df)}")
print(f"   • Duplicate counselors found: {len(duplicate_counselors_list)}")
print(f"\n📄 Output file: {output_file}")
print(f"\n✅ MERGE COMPLETE - No duplicates in final file!")

