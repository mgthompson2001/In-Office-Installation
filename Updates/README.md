# Updates Master Control Center

This is your master control center for managing all bot updates.

## How It Works

1. **You make changes** to bots in your master folder (`In-Office Installation/`)
2. **Run `sync_to_gdrive.py`** to push updates to company G-Drive
3. **Employees' bots** check G-Drive for updates automatically
4. **Employees get prompted** to update when new versions are available

## Quick Start

1. **Configure G-Drive path** in `config.json` (or run `get_gdrive_helper.py`)
2. **Set up version tracking:** Run `python setup_all_bots.py`
3. **Push updates:** Run `python sync_to_gdrive.py`

## Files

- **`config.json`** - Configuration (G-Drive path, bot settings)
- **`sync_to_gdrive.py`** - Push updates to G-Drive
- **`release_update.py`** - Release new version
- **`setup_all_bots.py`** - One-time setup
- **`get_gdrive_helper.py`** - Find G-Drive path automatically

## See QUICK_START.md for detailed instructions
