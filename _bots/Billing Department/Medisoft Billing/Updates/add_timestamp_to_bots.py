"""
Add timestamp to bot headers when syncing updates.
This script adds "Updated, MM/DD/YYYY" to bot titles/headers.
"""

import re
from pathlib import Path
from datetime import datetime

def add_timestamp_to_bot_file(bot_file_path, timestamp_str=None):
    """
    Add or update timestamp in bot file header/title.
    
    Args:
        bot_file_path: Path to bot's main Python file
        timestamp_str: Timestamp string (e.g., "11/26/2025"). If None, uses today's date.
    """
    if timestamp_str is None:
        timestamp_str = datetime.now().strftime("%m/%d/%Y")
    
    timestamp_text = f"Updated, {timestamp_str}"
    
    try:
        # Read file
        with open(bot_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern 1: Update existing timestamp
        pattern1 = r'Updated,?\s*\d{1,2}/\d{1,2}/\d{4}'
        if re.search(pattern1, content):
            content = re.sub(pattern1, timestamp_text, content)
        
        # Pattern 2: Add to root.title() calls
        pattern2 = r'(self\.root\.title\(["\'])([^"\']+)(["\'])'
        def add_to_title(match):
            title = match.group(2)
            # Don't add if already has timestamp
            if "Updated," not in title:
                return f'{match.group(1)}{title} - {timestamp_text}{match.group(3)}'
            return match.group(0)
        content = re.sub(pattern2, add_to_title, content)
        
        # Pattern 3: Add to title= parameters
        pattern3 = r'(title\s*=\s*["\'])([^"\']+)(["\'])'
        def add_to_title_param(match):
            title = match.group(2)
            if "Updated," not in title:
                return f'{match.group(1)}{title} - {timestamp_text}{match.group(3)}'
            return match.group(0)
        content = re.sub(pattern3, add_to_title_param, content)
        
        # Pattern 4: Add to header labels (common pattern)
        pattern4 = r'(text\s*=\s*["\'])([^"\']*Bot[^"\']*)(["\'])'
        def add_to_header(match):
            text = match.group(2)
            if "Updated," not in text and len(text) < 50:  # Only short titles
                return f'{match.group(1)}{text} - {timestamp_text}{match.group(3)}'
            return match.group(0)
        content = re.sub(pattern4, add_to_header, content, count=1)  # Only first match
        
        # Only write if changed
        if content != original_content:
            with open(bot_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error updating {bot_file_path}: {e}")
        return False


def add_timestamps_to_all_bots_in_folder(bot_folder, timestamp_str=None):
    """Add timestamps to all bot files in a folder"""
    if timestamp_str is None:
        timestamp_str = datetime.now().strftime("%m/%d/%Y")
    
    bot_path = Path(bot_folder)
    updated_count = 0
    
    # Find main bot Python files
    for py_file in bot_path.glob("*bot*.py"):
        if py_file.is_file() and py_file.name != "update_bot.py":
            if add_timestamp_to_bot_file(py_file, timestamp_str):
                updated_count += 1
                print(f"✅ Updated timestamp in {py_file.name}")
    
    return updated_count


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        bot_folder = sys.argv[1]
        timestamp = sys.argv[2] if len(sys.argv) > 2 else None
        add_timestamps_to_all_bots_in_folder(bot_folder, timestamp)
    else:
        print("Usage: python add_timestamp_to_bots.py <bot_folder> [timestamp]")
        print("Example: python add_timestamp_to_bots.py \"_bots\\Billing Department\\Medisoft Billing\" \"11/26/2025\"")

