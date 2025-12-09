"""
Helper to add timestamps to bot files when syncing.
Called by sync_to_gdrive.py
"""

import re
from pathlib import Path
from datetime import datetime

def add_timestamp_to_bot_file(bot_file_path, timestamp_str=None):
    """Add or update timestamp in bot file"""
    if timestamp_str is None:
        timestamp_str = datetime.now().strftime("%m/%d/%Y")
    
    timestamp_text = f"Updated, {timestamp_str}"
    
    try:
        with open(bot_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Update existing timestamp
        pattern1 = r'Updated,?\s*\d{1,2}/\d{1,2}/\d{4}'
        content = re.sub(pattern1, timestamp_text, content)
        
        # Add to root.title()
        pattern2 = r'(self\.root\.title\(["\'])([^"\']+)(["\'])'
        def add_to_title(match):
            title = match.group(2)
            if "Updated," not in title:
                return f'{match.group(1)}{title} - {timestamp_text}{match.group(3)}'
            return match.group(0)
        content = re.sub(pattern2, add_to_title, content)
        
        # DO NOT Add to title label text - UI headers should only show bot name
        # Window titles (root.title) will have timestamps, but UI headers (tk.Label) should NOT
        
        if content != original:
            with open(bot_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"   ⚠️  Error updating {bot_file_path.name}: {e}")
        return False

