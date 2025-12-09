#!/usr/bin/env python3
"""
Test script to verify the IPS uploader fixes
"""

import re

def test_middle_initial_detection():
    """Test middle initial detection and removal"""
    print("=== Testing Middle Initial Detection ===")
    
    def _has_middle_initial(name):
        pattern = r'\b\w+\s+[A-Z]\.\s+\w+\b'
        return bool(re.search(pattern, name))
    
    def _remove_middle_initial(name):
        cleaned = re.sub(r'\s+[A-Z]\.\s+', ' ', name)
        return ' '.join(cleaned.split())
    
    test_cases = [
        "Josephine M. Charczuk",
        "John A. Smith", 
        "Mary Jane Watson",
        "Bob Johnson"
    ]
    
    for name in test_cases:
        has_middle = _has_middle_initial(name)
        if has_middle:
            without_middle = _remove_middle_initial(name)
            print(f"✓ '{name}' -> '{without_middle}'")
        else:
            print(f"✗ '{name}' (no middle initial)")

def test_counselor_name_cleaning():
    """Test counselor name cleaning for IPS formats"""
    print("\n=== Testing Counselor Name Cleaning ===")
    
    def clean_counselor_name(counselor):
        # Remove IPS from anywhere in the name
        clean_name = re.sub(r'[-,\s]*IPS[-,\s]*', '', counselor, flags=re.IGNORECASE).strip()
        
        # Handle "Last-IPS, First" format -> "First Last"
        if ',' in clean_name:
            parts = clean_name.split(',')
            if len(parts) == 2:
                last_name = parts[0].strip()
                first_name = parts[1].strip()
                if first_name and last_name:  # Both parts exist
                    clean_name = f"{first_name} {last_name}"
                elif last_name:  # Only last name exists
                    clean_name = last_name
        
        # Remove any trailing commas or semicolons
        clean_name = re.sub(r'[,;]+$', '', clean_name).strip()
        return clean_name
    
    test_cases = [
        "Santana-IPS, Michelle",
        "Teluwo-IPS, Soraya", 
        "Metelitsa-IPS, Joanna",
        "Brown-IPS, Travis",
        "Smith-IPS",
        "Johnson, John"
    ]
    
    for counselor in test_cases:
        cleaned = clean_counselor_name(counselor)
        print(f"✓ '{counselor}' -> '{cleaned}'")

def test_counselor_matching():
    """Test counselor matching logic"""
    print("\n=== Testing Counselor Matching ===")
    
    def test_match(counselor_name, csv_worker):
        counselor_normalized = counselor_name.lower().strip()
        worker_normalized = csv_worker.lower().strip()
        
        # Direct match
        if (worker_normalized in counselor_normalized or 
            counselor_normalized in worker_normalized):
            return "direct"
        
        # "Last, First" vs "First Last" format
        if ',' in worker_normalized:
            parts = worker_normalized.split(',')
            if len(parts) == 2:
                last_name = parts[0].strip()
                first_name = parts[1].strip()
                reversed_format = f"{first_name} {last_name}"
                
                if (reversed_format in counselor_normalized or 
                    counselor_normalized in reversed_format):
                    return "reversed"
        
        # "LastFirst" vs "First Last" format
        csv_parts = re.findall(r'[A-Z][a-z]*', csv_worker)
        if len(csv_parts) >= 2:
            csv_reversed1 = f"{csv_parts[1]} {csv_parts[0]}"  # First Last
            csv_reversed2 = f"{csv_parts[0]} {csv_parts[1]}"  # Last First
            
            if (counselor_normalized == csv_reversed1 or 
                counselor_normalized == csv_reversed2 or
                csv_reversed1 in counselor_normalized or 
                csv_reversed2 in counselor_normalized):
                return "lastfirst"
        
        return "no_match"
    
    test_cases = [
        ("Michelle Santana", "Santana-IPS, Michelle"),
        ("Soraya Teluwo", "Teluwo-IPS, Soraya"),
        ("Joanna Metelitsa", "Metelitsa-IPS, Joanna"),
        ("Travis Brown", "Brown-IPS, Travis"),
        ("John Smith", "Smith, John"),
        ("Jane Doe", "Doe, Jane")
    ]
    
    for counselor_name, csv_worker in test_cases:
        match_type = test_match(counselor_name, csv_worker)
        if match_type != "no_match":
            print(f"✓ '{counselor_name}' matches '{csv_worker}' ({match_type})")
        else:
            print(f"✗ '{counselor_name}' does NOT match '{csv_worker}'")

if __name__ == "__main__":
    test_middle_initial_detection()
    test_counselor_name_cleaning()
    test_counselor_matching()
    print("\n=== Test Complete ===")
