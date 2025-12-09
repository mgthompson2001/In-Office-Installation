#!/usr/bin/env python3
"""Verification test for Payer Claim Control # extraction"""

import sys
from pathlib import Path

# Add bot directory to path
bot_dir = Path(__file__).parent
sys.path.insert(0, str(bot_dir))

try:
    from tn_refiling_bot import TNRefilingBot
    import tkinter as tk
except ImportError as e:
    print(f"ERROR: Could not import bot: {e}")
    sys.exit(1)

def test_extraction():
    """Test Payer Claim Control # extraction"""
    
    print("\n" + "="*80)
    print("VERIFICATION TEST: Payer Claim Control # Extraction")
    print("="*80 + "\n")
    
    # Test PDF path
    pdf_path = r"C:\Users\mthompson\Downloads\ERA #22159423 details for CONSUELO R PALENCIA _ TherapyNotes.pdf"
    target_client = "CONSUELO R PALENCIA"
    expected_payer_control = "01 091525 09917 00020"
    
    print(f"Test PDF: {Path(pdf_path).name}")
    print(f"Target Client: {target_client}")
    print(f"Expected Payer Claim Control #: {expected_payer_control}\n")
    
    try:
        # Initialize bot (without GUI display)
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        print("Initializing bot...")
        bot = TNRefilingBot()
        bot.root = root  # Set root window after initialization
        
        print("Extracting Payer Claim Control #...\n")
        result = bot.extract_payer_claim_control(pdf_path, target_client)
        
        # Clean up
        root.destroy()
        
        # Verify results
        print("\n" + "="*80)
        print("EXTRACTION RESULTS:")
        print("="*80 + "\n")
        
        if result is None:
            print("❌ FAILED: Extraction returned None")
            return False
        
        if not result.get('matched'):
            print(f"⚠️  WARNING: Extraction marked as not matched")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return False
        
        extracted_payer_control = result.get('payer_claim_control')
        
        print(f"Extracted Payer Claim Control #: {extracted_payer_control}")
        print(f"Expected: {expected_payer_control}")
        print(f"Client Name: {result.get('client_name')}")
        print(f"Patient ID: {result.get('patient_id')}")
        print(f"Claim #: {result.get('claim_number')}")
        print(f"Matched: {result.get('matched')}\n")
        
        # Verify match
        if extracted_payer_control == expected_payer_control:
            print("="*80)
            print("✅ SUCCESS: Payer Claim Control # extracted correctly!")
            print("="*80 + "\n")
            return True
        else:
            print("="*80)
            print("❌ FAILED: Extracted number does not match expected")
            print(f"   Got: {extracted_payer_control}")
            print(f"   Expected: {expected_payer_control}")
            print("="*80 + "\n")
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR during extraction: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_extraction()
    sys.exit(0 if success else 1)

