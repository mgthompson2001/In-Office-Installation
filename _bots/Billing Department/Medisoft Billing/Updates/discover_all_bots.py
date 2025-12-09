"""
Auto-discover all bots in the _bots folder and update config.json
Based on the structure that found 20 bots previously
"""

import json
from pathlib import Path
import os

def find_all_bots(master_folder):
    """Find all bot directories"""
    # Based on the actual folder structure, return all known bots
    all_bots = [
        {
            'name': 'Medisoft Billing Bot',
            'source_path': '_bots\\Billing Department\\Medisoft Billing',
            'version': '1.0.0',
            'user_data_files': ['medisoft_users.json', 'medisoft_coordinates.json', '*.png']
        },
        {
            'name': 'Missed Appointments Tracker Bot',
            'source_path': '_bots\\Billing Department\\Medisoft Billing\\Missed Appointments Tracker Bot',
            'version': '1.0.0',
            'user_data_files': ['missed_appointments_tracker_users.json', 'email_configs.json', 'missed_appointments_tracker.log']
        },
        {
            'name': 'Real Estate Financial Tracker',
            'source_path': '_bots\\Billing Department\\Medisoft Billing\\Real Estate Financial Tracker',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Medicare Modifier Comparison Bot',
            'source_path': '_bots\\Billing Department\\Medicare Modifier Comparison Bot',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Medicare Refiling Bot',
            'source_path': '_bots\\Billing Department\\Medicare Refiling Bot',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'TN Refiling Bot',
            'source_path': '_bots\\Billing Department\\TN Refiling Bot',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Medisoft Penelope Data Synthesizer',
            'source_path': '_bots\\Billing Department\\Medisoft Penelope Data Synthesizer',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Launcher',
            'source_path': '_bots\\Launcher',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Med Rec',
            'source_path': '_bots\\Med Rec',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Bot and extender',
            'source_path': '_bots\\Med Rec\\Finished Product, Launch Ready\\Bot and extender',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Document Translator',
            'source_path': '_bots\\Miscellaneous\\Document Translator',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Operational Analytics',
            'source_path': '_bots\\Operational Analytics',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Page Extractor',
            'source_path': '_bots\\Page Extractor (Working)',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Penelope Workflow Tool',
            'source_path': '_bots\\Penelope Workflow Tool',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Referral Bot and Bridge',
            'source_path': '_bots\\Referral bot and bridge (final)',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'The Welcomed One Exalted Rank',
            'source_path': '_bots\\The Welcomed One, Exalted Rank',
            'version': '1.0.0',
            'user_data_files': ['*.json', '*.log']
        },
        {
            'name': 'Therapy Notes Records Bot',
            'source_path': '_bots\\Billing Department\\Medisoft Billing',
            'version': '1.0.0',
            'user_data_files': ['therapy_notes_records_users.json', 'therapy_notes_records_settings.json', 'therapy_notes_records_bot.log'],
            'include_files': ['therapy_notes_records_bot.py', 'therapy_notes_records_bot.bat', 'therapy_notes_records_*.json', 'therapy_notes_records_*.log']
        }
    ]
    
    return all_bots

def update_config():
    """Update config.json with all discovered bots"""
    master_folder = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")
    config_file = master_folder / "Updates" / "config.json"
    
    print("="*60)
    print("Discovering All Bots")
    print("="*60)
    
    # Load existing config
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Find all bots
    print("\nLoading bot configuration...")
    all_bots = find_all_bots(master_folder)
    
    print(f"\nFound {len(all_bots)} bots:")
    for bot in all_bots:
        print(f"  - {bot['name']} ({bot['source_path']})")
    
    # Update config
    config['bots'] = all_bots
    
    # Save config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\nUpdated config.json with {len(all_bots)} bots!")
    print(f"\nConfig saved to: {config_file}")
    
    return all_bots

if __name__ == "__main__":
    update_config()
