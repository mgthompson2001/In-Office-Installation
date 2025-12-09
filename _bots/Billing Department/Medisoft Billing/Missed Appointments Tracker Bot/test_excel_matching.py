"""
Test script to verify Excel data loading and matching between Clients and Counselors
"""
import sys
from pathlib import Path

# Add the current directory to path to import the bot
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    import pandas as pd
    EXCEL_AVAILABLE = True
except ImportError:
    print("❌ pandas is not available. Please install it with: pip install pandas openpyxl")
    EXCEL_AVAILABLE = False
    sys.exit(1)

from missed_appointments_tracker_bot import Client, Counselor, FrequencyType, MissedAppointmentsTrackerBot

def load_clients_excel(file_path: Path):
    """Load clients from Excel file"""
    print(f"\n[INFO] Loading clients from: {file_path}")
    
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return []
    
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        print(f"   Found {len(df)} row(s) in clients Excel")
        
        clients = []
        error_count = 0
        for idx, row in df.iterrows():
            try:
                # Extract client data using same column names as bot
                last_name = str(row.get('Last_Name', '')).strip() if pd.notna(row.get('Last_Name')) else ""
                first_name = str(row.get('First_Name', '')).strip() if pd.notna(row.get('First_Name')) else ""
                
                if not last_name and not first_name:
                    continue
                
                full_name = f"{first_name} {last_name}".strip()
                counselor_name = str(row.get('Counselor', '')).strip() if pd.notna(row.get('Counselor')) else ""
                frequency_text = str(row.get('Frequency', '')).strip() if pd.notna(row.get('Frequency')) else ""
                
                if not full_name or full_name.lower() in ['nan', 'none', '']:
                    continue
                
                # Create client object with all required fields
                client = Client(
                    name=full_name,
                    last_name=last_name,
                    first_name=first_name,
                    counselor_name=counselor_name,
                    frequency_text=frequency_text,
                    frequency_type=FrequencyType.UNKNOWN,
                    sessions_per_period=0,
                    reassigned=False,
                    raw_data=row.to_dict()
                )
                clients.append(client)
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # Only show first 5 errors
                    print(f"   [WARNING] Error processing row {idx}: {str(e)}")
                continue
        
        if error_count > 5:
            print(f"   [WARNING] ... and {error_count - 5} more errors")
        print(f"   [SUCCESS] Loaded {len(clients)} client(s)")
        return clients
    except Exception as e:
        print(f"   [ERROR] Error loading clients Excel: {str(e)}")
        return []

def load_counselors_excel(file_path: Path):
    """Load counselors from Excel file"""
    print(f"\n[INFO] Loading counselors from: {file_path}")
    
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return []
    
    try:
        # Read from "ISWS Counselors" sheet (same as bot)
        df = pd.read_excel(file_path, sheet_name='ISWS Counselors', engine='openpyxl')
        print(f"   Found {len(df)} row(s) in counselors Excel")
        
        counselors = []
        for idx, row in df.iterrows():
            try:
                # Extract counselor data using same column names as bot
                last_name = str(row.get('Last Name', '')).strip() if pd.notna(row.get('Last Name')) else ""
                first_name = str(row.get('First Name', '')).strip() if pd.notna(row.get('First Name')) else ""
                
                if not last_name and not first_name:
                    continue
                
                # Counselor name format: "Last, First"
                counselor_name = f"{last_name}, {first_name}"
                
                # Check if terminated
                date_of_term = None
                is_active = True
                if pd.notna(row.get('Date of Term')):
                    date_of_term = str(row.get('Date of Term'))
                    is_active = False
                
                # Create counselor object
                counselor = Counselor(
                    name=counselor_name,
                    last_name=last_name,
                    first_name=first_name,
                    date_of_termination=date_of_term,
                    is_active=is_active,
                    raw_data=row.to_dict()
                )
                counselors.append(counselor)
            except Exception as e:
                print(f"   [WARNING] Error processing row {idx}: {str(e)}")
                continue
        
        print(f"   [SUCCESS] Loaded {len(counselors)} counselor(s)")
        return counselors
    except Exception as e:
        print(f"   [ERROR] Error loading counselors Excel: {str(e)}")
        return []

def test_matching(clients, counselors):
    """Test how clients match to counselors"""
    print(f"\n[INFO] Testing matching between {len(clients)} clients and {len(counselors)} counselors...")
    
    # Get unique counselor names from clients
    client_counselor_names = set()
    for client in clients:
        if client.counselor_name:
            client_counselor_names.add(client.counselor_name)
    
    # Get counselor names from counselors list
    counselor_names = {c.name for c in counselors}
    
    print(f"\n   Client Excel has {len(client_counselor_names)} unique counselor names")
    print(f"   Counselor Excel has {len(counselor_names)} counselor names")
    
    # Test matching
    exact_matches = 0
    fuzzy_matches = 0
    unmatched = []
    
    for client_counselor in client_counselor_names:
        if client_counselor in counselor_names:
            exact_matches += 1
        else:
            # Try fuzzy matching using the bot's method
            bot = MissedAppointmentsTrackerBot()
            matched_counselor = bot._fuzzy_match_counselor(client_counselor, counselors)
            if matched_counselor:
                matched = matched_counselor.name
                fuzzy_matches += 1
                print(f"   [MATCH] Fuzzy matched: '{client_counselor}' -> '{matched}'")
            else:
                unmatched.append(client_counselor)
    
    print(f"\n   [SUMMARY] Matching Summary:")
    print(f"      - Exact matches: {exact_matches}")
    print(f"      - Fuzzy matches: {fuzzy_matches}")
    print(f"      - Unmatched: {len(unmatched)}")
    
    if unmatched:
        print(f"\n   [WARNING] Unmatched counselor names (showing first 20):")
        for name in list(unmatched)[:20]:
            print(f"      - '{name}'")
    
    # Show sample data
    print(f"\n   [INFO] Sample client counselor names from Excel:")
    sample_client_counselors = list(client_counselor_names)[:5]
    for name in sample_client_counselors:
        print(f"      - '{name}'")
    
    print(f"\n   [INFO] Sample counselor names from Master List:")
    sample_counselors = list(counselor_names)[:5]
    for name in sample_counselors:
        print(f"      - '{name}'")
    
    # Group clients by counselor
    print(f"\n   [INFO] Grouping clients by counselor...")
    clients_by_counselor = {}
    for client in clients:
        if client.counselor_name:
            if client.counselor_name not in clients_by_counselor:
                clients_by_counselor[client.counselor_name] = []
            clients_by_counselor[client.counselor_name].append(client)
    
    print(f"   [SUCCESS] Grouped clients into {len(clients_by_counselor)} counselor groups")
    
    # Show top counselors by client count
    print(f"\n   [INFO] Top 10 counselors by client count:")
    sorted_counselors = sorted(clients_by_counselor.items(), key=lambda x: len(x[1]), reverse=True)
    for counselor_name, counselor_clients in sorted_counselors[:10]:
        print(f"      - {counselor_name}: {len(counselor_clients)} client(s)")

def main():
    """Main test function"""
    print("=" * 60)
    print("Excel Data Matching Test")
    print("=" * 60)
    
    # File paths
    clients_file = Path(r"G:\Company\Client List - Master\ODBC NEW Client List.xlsx")
    counselors_file = Path(r"G:\Company\Master Counselor\Master Counselor List.xlsx")
    
    # Load data
    clients = load_clients_excel(clients_file)
    counselors = load_counselors_excel(counselors_file)
    
    if not clients:
        print("\n[ERROR] No clients loaded. Cannot continue.")
        return
    
    if not counselors:
        print("\n[ERROR] No counselors loaded. Cannot continue.")
        return
    
    # Test matching
    test_matching(clients, counselors)
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()

