"""
Fix config.json to only include actual bots, not parent folders
"""

import json
from pathlib import Path

def fix_config():
    """Remove parent/container folders from bots list"""
    master_folder = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")
    config_file = master_folder / "Updates" / "config.json"
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Folders to exclude (not actual bots)
    exclude_names = [
        "_bots",
        "Billing Department",
        "Miscellaneous",
        "Med Rec",  # This might be a folder, check if it has actual bot files
    ]
    
    # Keep only actual bots
    actual_bots = []
    for bot in config['bots']:
        bot_name = bot['name']
        source_path = bot['source_path']
        
        # Skip if it's a parent folder
        if bot_name in exclude_names:
            print(f"Skipping folder (not a bot): {bot_name}")
            continue
        
        # Skip if path is too short (likely a parent folder)
        if source_path.count('\\') < 2:
            print(f"Skipping parent folder: {bot_name} ({source_path})")
            continue
        
        actual_bots.append(bot)
    
    # Update config
    config['bots'] = actual_bots
    
    # Save
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Fixed config! Now has {len(actual_bots)} actual bots:")
    for bot in actual_bots:
        print(f"  - {bot['name']}")

if __name__ == "__main__":
    fix_config()

