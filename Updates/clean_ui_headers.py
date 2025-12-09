"""
Script to clean version info from UI headers (tk.Label) in all bots
This removes "Version X.X, Last Updated..." from UI headers but keeps window titles
"""

import re
from pathlib import Path
from typing import List, Tuple

def clean_version_from_text(text: str) -> str:
    """Remove version and date info from text"""
    # Remove weird patterns like "-, -, -, - Version X.X, Last Updated..."
    text = re.sub(r'\s*-\s*,\s*-\s*,\s*-\s*,\s*-\s*Version\s+[\d.]+,\s*Last Updated\s+\d{1,2}/\d{1,2}/\d{4}', '', text)
    # Remove patterns like " - Version 2.1.0, Last Updated 12/03/2025"
    text = re.sub(r'\s*-\s*Version\s+[\d.]+,\s*Last Updated\s+\d{1,2}/\d{1,2}/\d{4}', '', text)
    text = re.sub(r'\s*-\s*Version\s+[\d.]+', '', text)
    text = re.sub(r'\s*Version\s+[\d.]+,\s*Last Updated\s+\d{1,2}/\d{1,2}/\d{4}', '', text)
    text = re.sub(r'\s*Last Updated\s+\d{1,2}/\d{1,2}/\d{4}', '', text)
    text = re.sub(r'\s*-\s*Updated,?\s*\d{1,2}/\d{1,2}/\d{4}', '', text)
    # Clean up trailing dashes and spaces
    text = re.sub(r'\s*-\s*$', '', text)
    text = re.sub(r'\s+$', '', text)
    return text.strip()

def clean_ui_headers_in_file(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Clean version info from UI headers (tk.Label) in a Python file
    Returns: (was_changed, list_of_changes)
    """
    if not file_path.exists() or not file_path.suffix == '.py':
        return False, []
    
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        changes = []
        
        # Pattern 1: tk.Label(header, text="Bot Name - Version X.X, Last Updated...")
        # Pattern 2: Label(header, text="Bot Name - Version X.X, Last Updated...")
        # Pattern 3: tk.Label(header_frame, text="Bot Name - Version X.X, Last Updated...")
        # Pattern 4: tk.Label(email_header, text="Bot Name - Version X.X, Last Updated...")
        # Pattern 5: tk.Label(title_frame, text="Bot Name - Version X.X, Last Updated...")
        # Pattern 6: tk.Label(..., text="Bot Name - Version X.X, Last Updated...", ...)
        
        # Match tk.Label or Label with text parameter containing version info
        label_patterns = [
            # Pattern: tk.Label(header, text="...", ...) or Label(header, text="...", ...)
            r'(tk\.Label\([^,)]+,\s*text\s*=\s*)(["\'])([^"\']*Version[^"\']*Last Updated[^"\']*)(["\'])',
            r'(Label\([^,)]+,\s*text\s*=\s*)(["\'])([^"\']*Version[^"\']*Last Updated[^"\']*)(["\'])',
            # Pattern: text="..." with Version and Last Updated
            r'(text\s*=\s*)(["\'])([^"\']*Version[^"\']*Last Updated[^"\']*)(["\'])',
        ]
        
        for pattern in label_patterns:
            def replace_label(match):
                prefix = match.group(1)
                quote1 = match.group(2)
                label_text = match.group(3)
                quote2 = match.group(4)
                
                # Only clean if it contains version info
                if 'Version' in label_text and 'Last Updated' in label_text:
                    cleaned_text = clean_version_from_text(label_text)
                    changes.append(f"Cleaned: '{label_text}' -> '{cleaned_text}'")
                    return f'{prefix}{quote1}{cleaned_text}{quote2}'
                
                return match.group(0)
            
            content = re.sub(pattern, replace_label, content)
        
        # Also handle cases where text might be on multiple lines
        # Pattern: text="Bot Name - Version X.X,\nLast Updated..."
        multiline_pattern = r'(text\s*=\s*)(["\'])([^"\']*Version[^"\']*)(["\'])\s*\+\s*["\']([^"\']*Last Updated[^"\']*)(["\'])'
        
        def replace_multiline(match):
            prefix = match.group(1)
            quote1 = match.group(2)
            part1 = match.group(3)
            quote2 = match.group(4)
            part2 = match.group(5)
            quote3 = match.group(6)
            
            # Clean both parts
            cleaned_part1 = clean_version_from_text(part1)
            if cleaned_part1:
                changes.append(f"Cleaned multiline: '{part1}...' -> '{cleaned_part1}'")
                return f'{prefix}{quote1}{cleaned_part1}{quote2}'
            else:
                # If part1 is empty after cleaning, just remove the whole thing
                return f'{prefix}{quote1}{quote2}'
        
        content = re.sub(multiline_pattern, replace_multiline, content)
        
        # Handle APP_TITLE variable assignments (e.g., APP_TITLE = "Bot Name - Version X.X, Last Updated...")
        app_title_pattern = r'(APP_TITLE\s*=\s*)(["\'])([^"\']*Version[^"\']*Last Updated[^"\']*)(["\'])'
        
        def replace_app_title(match):
            prefix = match.group(1)
            quote1 = match.group(2)
            title_text = match.group(3)
            quote2 = match.group(4)
            
            # Clean version info
            cleaned_text = clean_version_from_text(title_text)
            if cleaned_text != title_text:
                changes.append(f"Cleaned APP_TITLE: '{title_text}' -> '{cleaned_text}'")
                return f'{prefix}{quote1}{cleaned_text}{quote2}'
            return match.group(0)
        
        content = re.sub(app_title_pattern, replace_app_title, content)
        
        # Write if changed
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True, changes
        
        return False, []
        
    except Exception as e:
        print(f"   ⚠️  Error processing {file_path.name}: {e}")
        return False, []

def find_all_bot_files(root_dir: Path) -> List[Path]:
    """Find all bot Python files"""
    bot_files = []
    
    # Exclude patterns
    excluded_names = ["update_bot.py", "add_timestamp", "discover_all", "setup_all", 
                     "release_update", "sync_to_gdrive", "__init__", "clean_ui_headers",
                     "test_", "setup_", "install_"]
    excluded_folders = ["Updates", "__pycache__", ".git", "_archive", 
                       "Cursor versions/Old stuff", "Cursor versions/Goose Backup (old)", 
                       "Cursor versions/Newest Goose Backup", "quarantine", "vendor"]
    
    for py_file in root_dir.rglob("*.py"):
        # Skip if in excluded folder
        if any(excluded in str(py_file) for excluded in excluded_folders):
            continue
        
        # Skip if filename contains excluded names
        if any(excluded in py_file.name.lower() for excluded in excluded_names):
            continue
        
        bot_files.append(py_file)
    
    return bot_files

def main():
    """Main function to clean all UI headers"""
    # Get the root directory (In-Office Installation)
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    
    print("="*60)
    print("Cleaning UI Headers - Removing Version Info")
    print("="*60)
    print(f"\nSearching for bot files in: {root_dir}")
    
    # Find all bot files
    bot_files = find_all_bot_files(root_dir)
    print(f"\nFound {len(bot_files)} bot files to check")
    
    # Clean each file
    cleaned_count = 0
    total_changes = 0
    
    for bot_file in bot_files:
        was_changed, changes = clean_ui_headers_in_file(bot_file)
        if was_changed:
            cleaned_count += 1
            total_changes += len(changes)
            print(f"\n[OK] {bot_file.relative_to(root_dir)}")
            for change in changes[:3]:  # Show first 3 changes
                print(f"   {change}")
            if len(changes) > 3:
                print(f"   ... and {len(changes) - 3} more changes")
    
    print(f"\n{'='*60}")
    print(f"[OK] Cleanup Complete!")
    print(f"{'='*60}")
    print(f"Files cleaned: {cleaned_count}/{len(bot_files)}")
    print(f"Total changes: {total_changes}")
    print(f"\nNote: Window titles (.title()) still have version info (as intended)")
    print(f"Only UI headers (tk.Label) were cleaned.")

if __name__ == "__main__":
    main()

