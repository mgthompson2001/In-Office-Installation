import os
from pathlib import Path

master_folder = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")
bots_folder = master_folder / "_bots"

exclude_dir_names = ["__pycache__", ".git", "quarantine", "Updates", "Installer", "Backup", "backup", "old", "Old"]
exclude_path_patterns = ["Cursor versions"]

bots = []
for root, dirs, files in os.walk(bots_folder):
    root_path = Path(root)
    root_str = str(root)
    
    skip_path = False
    for pattern in exclude_path_patterns:
        if pattern in root_str:
            skip_path = True
            break
    if skip_path:
        continue
    
    has_python = any(f.endswith('.py') for f in files)
    has_bat = any(f.endswith('.bat') for f in files)
    
    if has_python or has_bat:
        try:
            rel_path = root_path.relative_to(master_folder)
            rel_str = str(rel_path).replace("/", "\\")
        except:
            continue
        
        if rel_str == "_bots":
            continue
        
        bot_name = root_path.name
        
        if bot_name in exclude_dir_names:
            continue
        
        bots.append({
            'name': bot_name,
            'source_path': rel_str
        })

print(f"Found {len(bots)} bots:")
for bot in sorted(bots, key=lambda x: x['source_path']):
    print(f"  - {bot['name']} ({bot['source_path']})")

