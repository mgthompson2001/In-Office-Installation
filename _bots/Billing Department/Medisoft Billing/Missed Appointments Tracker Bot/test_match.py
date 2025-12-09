"""Test the matching function"""

import re

def normalize_name(name):
    """Normalize name for comparison"""
    if not name:
        return ""
    name = str(name).strip().lower()
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def extract_name_parts(name):
    """Extract last and first name parts from various formats"""
    if not name:
        return None, None
    
    name = str(name).strip()
    
    if ',' in name:
        parts = [p.strip() for p in name.split(',', 1)]
        if len(parts) == 2:
            return normalize_name(parts[0]), normalize_name(parts[1])
    
    parts = name.split()
    if len(parts) >= 2:
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

# Test cases
test_cases = [
    ("Agenor, Monde", "Agenor, Monde"),
    ("Alam, Sumera F.", "Alam, Sumera F."),
    ("Alcaide, Melissa", "Alcaide, Melissa"),
    ("Alers, Alexander", "Alers, Alexander"),
]

for name1, name2 in test_cases:
    result = names_match(name1, name2)
    print(f"'{name1}' vs '{name2}': {result}")

