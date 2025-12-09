"""
Helper script to add version and last updated date to bot headers
This is called during the sync process to update all bot files
"""

import re
from pathlib import Path
from datetime import datetime
import json
import os


def clean_existing_version_text(text: str) -> str:
    """Remove any existing version/date text and weird characters"""
    # Remove weird patterns like "-, -, -, - Version X.X, Last Updated..."
    text = re.sub(r'\s*-\s*,\s*-\s*,\s*-\s*,\s*-\s*Version\s+[\d.]+,\s*Last Updated\s+\d{1,2}/\d{1,2}/\d{4}', '', text)
    # Remove normal version/date patterns
    text = re.sub(r'\s*-\s*Updated,?\s*\d{1,2}/\d{1,2}/\d{4}', '', text)
    text = re.sub(r'\s*Version\s+[\d.]+', '', text)
    text = re.sub(r'\s*Last Updated\s+\d{1,2}/\d{1,2}/\d{4}', '', text)
    text = re.sub(r'\s*v[\d.]+', '', text)  # Remove "v1.0" patterns
    # Clean up any trailing dashes or commas
    text = re.sub(r'\s*[-,\s]+$', '', text)
    return text.strip()


def add_version_and_date_to_bot(bot_file_path: Path, version: str, update_date: str = None):
    """
    Adds or updates version and date in WINDOW TITLES ONLY (.title() calls).
    
    CRITICAL: This function does NOT modify UI headers (tk.Label widgets) or APP_TITLE variables.
    UI headers must remain clean (bot name only) - version info only goes in window titles.
    
    Args:
        bot_file_path: Path to the bot Python file
        version: Version string (e.g., "1.3.1")
        update_date: Date string (e.g., "12/15/2024"). If None, uses current date.
    
    Returns:
        True if file was updated, False if no changes were needed (already correct or no title() calls)
    """
    if not bot_file_path.exists():
        return False
    
    if update_date is None:
        update_date = datetime.now().strftime("%m/%d/%Y")
    
    try:
        content = bot_file_path.read_text(encoding='utf-8')
        original_content = content
        
        # 1. Update root.title() calls ONLY (NOT APP_TITLE - that's used in UI headers!)
        # Pattern: self.root.title("Bot Name") or root.title("Bot Name") or super().__init__() + self.title(...)
        title_patterns = [
            r'(self\.root\.title\(|root\.title\()\s*(["\'])([^"\']+?)(["\'])',  # root.title("...")
            r'(self\.title\(|\.title\()\s*(["\'])([^"\']+?)(["\'])',  # self.title("...")
            # NOTE: APP_TITLE is NOT included here because it's used in UI headers (tk.Label)
        ]
        
        for title_pattern in title_patterns:
            def replace_title(match):
                prefix = match.group(1)
                quote1 = match.group(2)
                bot_name = match.group(3)
                quote2 = match.group(4)
                
                # Clean existing version/date
                bot_name_clean = clean_existing_version_text(bot_name)
                
                # Add version and date
                new_title = f'{bot_name_clean} - Version {version}, Last Updated {update_date}'
                return f'{prefix}{quote1}{new_title}{quote2}'
            
            content = re.sub(title_pattern, replace_title, content)
        
        # 2. DO NOT Update header Label widgets - UI headers should only show bot name
        # Window titles (root.title) will have version info, but UI headers (tk.Label) should NOT
        
        # 3. DO NOT Update APP_TITLE - it's used in UI headers (tk.Label(header, text=APP_TITLE, ...))
        # APP_TITLE should remain clean (bot name only) so UI headers don't show version info
        
        # 4. Handle cases where APP_TITLE is used directly in window titles
        # Pattern: self.title(APP_TITLE) or root.title(APP_TITLE)
        # We want to change these to: self.title(f"{APP_TITLE} - Version X.X, Last Updated...")
        # But leave APP_TITLE itself unchanged (it's used in UI headers)
        app_title_in_title_pattern = r'(self\.title\(|root\.title\(|\.title\()\s*(APP_TITLE)\s*\)'
        
        def replace_app_title_in_title(match):
            prefix = match.group(1)
            # Change to f-string format with version info
            # Use double braces {{ }} to escape braces in f-string output
            return f'{prefix}f"{{APP_TITLE}} - Version {version}, Last Updated {update_date}")'
        
        content = re.sub(app_title_in_title_pattern, replace_app_title_in_title, content)
        
        # 5. Handle f-strings in self.title() calls: self.title(f"{APP_TITLE} v{VERSION}")
        # If APP_TITLE already has version/date, don't add it again
        fstring_title_pattern = r'(self\.title\(|\.title\()\s*(f?["\'])([^"\']*APP_TITLE[^"\']*)(["\'])'
        
        def replace_fstring_title(match):
            prefix = match.group(1)
            quote1 = match.group(2)
            fstring_content = match.group(3)
            quote2 = match.group(4)
            
            # Only update if it contains APP_TITLE
            if 'APP_TITLE' in fstring_content:
                # Check if already has version/date
                if 'Version' in fstring_content and 'Last Updated' in fstring_content:
                    # Already has version/date, just return as-is
                    return match.group(0)
                
                # For f-strings with APP_TITLE, append the version/date
                # Example: f"{APP_TITLE}" -> f"{APP_TITLE} - Version X.X, Last Updated..."
                if 'v{VERSION}' in fstring_content or 'VERSION' in fstring_content:
                    # Remove version part and add our version/date
                    cleaned = re.sub(r'\s*v\{VERSION\}', '', fstring_content)
                    new_content = f'{cleaned} - Version {version}, Last Updated {update_date}'
                else:
                    new_content = f'{fstring_content} - Version {version}, Last Updated {update_date}'
                return f'{prefix}{quote1}{new_content}{quote2}'
            
            return match.group(0)
        
        content = re.sub(fstring_title_pattern, replace_fstring_title, content)
        
        # Only write if content changed
        if content != original_content:
            bot_file_path.write_text(content, encoding='utf-8')
            return True
        
        return False
        
    except Exception as e:
        print(f"   Warning: Error updating {bot_file_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def add_version_date_to_all_bots(master_folder: Path, version: str, update_date: str = None):
    """
    Find all bot Python files in _bots folder and add version/date to headers
    
    Args:
        master_folder: Root folder (In-Office Installation)
        version: Version string
        update_date: Date string (optional)
    """
    if update_date is None:
        update_date = datetime.now().strftime("%m/%d/%Y")
    
    bots_folder = master_folder / "_bots"
    if not bots_folder.exists():
        print(f"Warning: _bots folder not found: {bots_folder}")
        return
    
    # Find ALL .py files in _bots (not just *bot*.py)
    all_py_files = list(bots_folder.rglob("*.py"))
    
    # Exclude update bot and helper files, and files in excluded folders
    excluded_names = ["update_bot.py", "add_timestamp", "discover_all", "setup_all", "release_update", "sync_to_gdrive", "__init__"]
    excluded_folders = ["Updates", "__pycache__", ".git", "_archive", "Cursor versions"]
    
    bot_files = []
    for py_file in all_py_files:
        # Skip if filename contains excluded names
        if any(excluded in py_file.name.lower() for excluded in excluded_names):
            continue
        # Skip if in excluded folder
        if any(excluded in str(py_file) for excluded in excluded_folders):
            continue
        # Skip if it's a test file or utility
        if py_file.name.startswith("test_") or py_file.name.startswith("setup_") or py_file.name.startswith("install_"):
            continue
        bot_files.append(py_file)
    
    print(f"\nAdding version and date to {len(bot_files)} bot files...")
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for bot_file in bot_files:
        try:
            result = add_version_and_date_to_bot(bot_file, version, update_date)
            if result:
                print(f"   ✅ Updated: {bot_file.relative_to(master_folder)}")
                updated_count += 1
            else:
                # File was processed but didn't need updating (already correct or no title() calls found)
                skipped_count += 1
        except Exception as e:
            print(f"   ❌ Error processing {bot_file.relative_to(master_folder)}: {e}")
            error_count += 1
    
    print(f"\n   📊 Summary:")
    print(f"      ✅ Updated: {updated_count} files")
    print(f"      ✓ Already correct/No changes needed: {skipped_count} files")
    if error_count > 0:
        print(f"      ❌ Errors: {error_count} files")
    print(f"      📁 Total processed: {len(bot_files)}/{len(bot_files)} bot files")


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) >= 3:
        master_folder = Path(sys.argv[1])
        version = sys.argv[2]
        update_date = sys.argv[3] if len(sys.argv) > 3 else None
        add_version_date_to_all_bots(master_folder, version, update_date)
