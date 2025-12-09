"""
Flexible Name Matching Module for Missed Appointments Tracker Bot

This module provides flexible name matching to find counselors in TherapyNotes
even when the name format differs from the master list.
"""

import re
from difflib import SequenceMatcher
import pandas as pd


def normalize_name(name):
    """Normalize a name for comparison by removing extra spaces, converting to lowercase, etc."""
    if not name or pd.isna(name):
        return ""
    # Remove extra whitespace, convert to lowercase
    normalized = re.sub(r'\s+', ' ', str(name).strip().lower())
    # Remove special characters except commas, hyphens, and periods
    normalized = re.sub(r'[^\w\s,\-\.]', '', normalized)
    return normalized


def extract_name_parts(name):
    """Extract last name and first name from various formats."""
    if not name or pd.isna(name):
        return None, None
    
    name_str = str(name).strip()
    
    # Format 1: "Last, First" or "Last, First M." or "Last, First \"Nickname\""
    if ',' in name_str:
        parts = [p.strip() for p in name_str.split(',', 1)]
        last_name = parts[0]
        first_part = parts[1] if len(parts) > 1 else ""
        # Remove quotes and nicknames
        first_part = re.sub(r'["\'].*?["\']', '', first_part)
        # Remove middle initial if present
        first_name = re.sub(r'\s+[A-Z]\.?\s*$', '', first_part).strip()
        return last_name, first_name
    
    # Format 2: "First Last" or "First M. Last"
    parts = name_str.split()
    if len(parts) >= 2:
        # Assume last word is last name, first word(s) are first name
        last_name = parts[-1]
        first_name = ' '.join(parts[:-1])
        # Remove middle initial
        first_name = re.sub(r'\s+[A-Z]\.?\s*', ' ', first_name).strip()
        return last_name, first_name
    
    return None, None


def name_similarity(name1, name2):
    """Calculate similarity between two names (0.0 to 1.0)."""
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Exact match after normalization
    if norm1 == norm2:
        return 1.0
    
    # Check if one contains the other (for partial matches)
    if norm1 in norm2 or norm2 in norm1:
        return 0.9
    
    # Extract name parts and compare
    last1, first1 = extract_name_parts(name1)
    last2, first2 = extract_name_parts(name2)
    
    if last1 and last2 and first1 and first2:
        # Normalize the parts
        last1_norm = normalize_name(last1)
        last2_norm = normalize_name(last2)
        first1_norm = normalize_name(first1)
        first2_norm = normalize_name(first2)
        
        # Compare last names
        last_sim = SequenceMatcher(None, last1_norm, last2_norm).ratio()
        # Compare first names
        first_sim = SequenceMatcher(None, first1_norm, first2_norm).ratio()
        
        # If last name matches well, be more lenient with first name
        if last_sim >= 0.9:
            # Last name is a strong match, first name can be more flexible
            return (last_sim * 0.7 + first_sim * 0.3)
        else:
            # Both names need to match well
            return (last_sim * 0.6 + first_sim * 0.4)
    
    # Fallback to string similarity
    return SequenceMatcher(None, norm1, norm2).ratio()


def find_counselor_flexible(driver, counselor_name, staff_elements, threshold=0.80):
    """
    Find a counselor in the Staff list using flexible name matching.
    
    Args:
        driver: Selenium WebDriver instance
        counselor_name: Name from master list (e.g., "Last, First")
        staff_elements: List of WebElements representing staff members
        threshold: Minimum similarity score (0.0 to 1.0) to consider a match
    
    Returns:
        WebElement if found, None otherwise
    """
    best_match = None
    best_score = 0.0
    best_text = ""
    
    for element in staff_elements:
        try:
            # Get the text from the element (this might be the name or contain the name)
            element_text = element.text.strip()
            
            if not element_text:
                continue
            
            # Calculate similarity
            score = name_similarity(counselor_name, element_text)
            
            if score > best_score:
                best_score = score
                best_match = element
                best_text = element_text
                
        except Exception as e:
            # Skip elements that can't be read
            continue
    
    if best_match and best_score >= threshold:
        print(f"   ✓ Found counselor '{counselor_name}' with similarity score: {best_score:.2f} (matched: '{best_text}')")
        return best_match
    else:
        if best_score > 0:
            print(f"   ⚠️  Counselor '{counselor_name}' not found (best match: '{best_text}' with score: {best_score:.2f}, threshold: {threshold})")
        else:
            print(f"   ⚠️  Counselor '{counselor_name}' not found in Staff list")
        return None


def find_by_last_name(driver, counselor_name, staff_elements):
    """Fallback: Find by last name only."""
    if ',' in counselor_name:
        last_name = counselor_name.split(',')[0].strip()
    else:
        last_name = counselor_name.split()[-1] if counselor_name.split() else ""
    
    if not last_name:
        return None
    
    last_name_lower = normalize_name(last_name)
    
    for element in staff_elements:
        try:
            element_text = element.text.strip()
            if last_name_lower in normalize_name(element_text):
                print(f"   ✓ Found counselor by last name only: '{counselor_name}' -> '{element_text}'")
                return element
        except:
            continue
    
    return None


def find_by_reversed_format(driver, counselor_name, staff_elements):
    """Fallback: Try reversed format (First Last instead of Last, First)."""
    if ',' not in counselor_name:
        return None
    
    last, first = counselor_name.split(',', 1)
    reversed_name = f"{first.strip()} {last.strip()}"
    
    for element in staff_elements:
        try:
            element_text = element.text.strip()
            score = name_similarity(reversed_name, element_text)
            if score >= 0.85:
                print(f"   ✓ Found counselor with reversed format: '{counselor_name}' -> '{element_text}' (score: {score:.2f})")
                return element
        except:
            continue
    
    return None


def find_counselor_with_fallbacks(driver, counselor_name, staff_elements=None):
    """
    Find counselor using multiple strategies with fallbacks.
    
    Args:
        driver: Selenium WebDriver instance
        counselor_name: Name from master list
        staff_elements: Optional list of staff elements (will be fetched if not provided)
    
    Returns:
        WebElement if found, None otherwise
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    # Get staff elements if not provided
    if staff_elements is None:
        try:
            # Try common selectors for staff list
            selectors = [
                "//a[contains(@href, '/staff/')]",
                "//a[contains(@class, 'staff')]",
                "//div[contains(@class, 'staff')]//a",
                "//table//a[contains(text(), ',')]",  # Names with commas
            ]
            
            for selector in selectors:
                try:
                    staff_elements = driver.find_elements(By.XPATH, selector)
                    if staff_elements:
                        break
                except:
                    continue
            
            if not staff_elements:
                # Fallback: get all links on the page
                staff_elements = driver.find_elements(By.TAG_NAME, "a")
        except Exception as e:
            print(f"   ⚠️  Error getting staff elements: {e}")
            return None
    
    # Strategy 1: Flexible matching with high threshold
    result = find_counselor_flexible(driver, counselor_name, staff_elements, threshold=0.80)
    if result:
        return result
    
    # Strategy 2: Flexible matching with lower threshold
    result = find_counselor_flexible(driver, counselor_name, staff_elements, threshold=0.70)
    if result:
        return result
    
    # Strategy 3: Last name only
    result = find_by_last_name(driver, counselor_name, staff_elements)
    if result:
        return result
    
    # Strategy 4: Reversed format
    result = find_by_reversed_format(driver, counselor_name, staff_elements)
    if result:
        return result
    
    return None


# Test function
def test_name_matching():
    """Test the name matching with known examples."""
    test_cases = [
        ("Basit, Amina", "Amina Basit", True),
        ("Mark, Kelisha", "Mark, Kelisha", True),
        ("Basso, Melissa", "Melissa Basso", True),
        ("Bechan, Monica", "Monica Bechan", True),
        ("Gonzalez, Pedro \"Tommy\"", "Pedro Gonzalez", True),
        ("Donnelly, Jennifer L.", "Jennifer Donnelly", True),
        ("Clarke, Daniel", "Daniel Clarke", True),
        ("Basit, Amina", "Basit, Amina", True),  # Exact match
    ]
    
    print("Testing name matching:")
    print("=" * 80)
    for name1, name2, should_match in test_cases:
        score = name_similarity(name1, name2)
        match = score >= 0.80
        status = "✓" if match == should_match else "✗"
        print(f"{status} '{name1}' vs '{name2}': score={score:.2f}, match={match}")
    print("=" * 80)


if __name__ == "__main__":
    test_name_matching()

