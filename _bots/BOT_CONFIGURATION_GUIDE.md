# Bot Configuration Transfer Guide

This guide explains how to properly transfer bots to a new computer while preserving all bot "memory" (saved configurations, selectors, coordinates, and user data).

## Overview

When you transfer the `_bots` folder to a new employee's computer, you need to ensure that:

1. **All Python dependencies are installed** - Run `INSTALL_BOTS.bat`
2. **All configuration files are copied** - These preserve bot memory
3. **Special configuration files are set up** - Some files are stored outside the bot folders

## Configuration Files by Bot

### Medisoft Billing Bot
**Location:** `Billing Department\Medisoft Billing\`

Required files:
- `medisoft_users.json` - Saved user credentials
- `medisoft_coordinates.json` - Saved coordinate training data
- `*.png` - Screenshot images for button recognition

### Penelope Workflow Tool
**Location:** `Penelope Workflow Tool\`

Required files:
- `penelope_users.json` - Saved user credentials

### Welcome Letter Bot
**Location:** `The Welcomed One, Exalted Rank\`

Required files:
- `welcome_bot_users.json` - Saved user credentials
- `%USERPROFILE%\Documents\ISWS Welcome\learned_pn_selectors.json` - **IMPORTANT:** This file is stored in the user's Documents folder, not in the bot folder!

**To transfer learned selectors:**
1. On the source computer, copy: `Documents\ISWS Welcome\learned_pn_selectors.json`
2. On the new computer, create folder: `Documents\ISWS Welcome\`
3. Copy the file to the new location

### TN Refiling Bot
**Location:** `Billing Department\TN Refiling Bot\`

Required files:
- `tn_users.json` - Saved user credentials
- `tn_coordinates.json` - Saved coordinate training data

### Medicare Refiling Bot
**Location:** `Billing Department\Medicare Refiling Bot\`

Required files:
- `medicare_users.json` - Saved user credentials
- `pdf_field_mapping_config.json` - PDF field mapping configuration

### Medical Records Bot
**Location:** `Med Rec\`

Required files:
- `therapy_notes_records_users.json` - Saved user credentials
- `therapy_notes_records_settings.json` - Bot settings

## Installation Steps for New Computer

1. **Copy the entire `_bots` folder** to the new computer
   - Maintain the folder structure exactly as it is
   - Include all subfolders and files

2. **Run `INSTALL_BOTS.bat`** from the root `In-Office Installation` folder
   - This installs all Python dependencies
   - This includes PDF creation libraries (PyPDF2, reportlab, fpdf2)
   - This includes web automation libraries (selenium, webdriver-manager)

3. **Copy special configuration files:**
   - Copy `learned_pn_selectors.json` to `Documents\ISWS Welcome\` (if it exists on source computer)
   - Create the folder if it doesn't exist

4. **Verify configuration:**
   - Run `VERIFY_BOT_CONFIGURATION.bat` to check all files are present
   - This will show which configuration files are missing

5. **Test each bot:**
   - Run each bot to ensure it starts correctly
   - If selectors are missing, the bot will need to be re-trained
   - If users are missing, add them through the bot's UI

## What Gets Preserved

✅ **Preserved automatically** (when folder is copied):
- User credentials (stored in `*_users.json` files)
- Coordinate training data (stored in `*_coordinates.json` files)
- PDF field mappings (stored in `pdf_field_mapping_config.json`)
- Bot settings (stored in `*_settings.json` files)
- Screenshot images (`.png` files for button recognition)

⚠️ **Requires manual transfer:**
- `learned_pn_selectors.json` - Stored in `Documents\ISWS Welcome\` (outside bot folder)

## Troubleshooting

### "Selectors not available" error
- The `learned_pn_selectors.json` file is missing or not in the correct location
- Copy it from the source computer to `Documents\ISWS Welcome\` on the new computer
- Or re-train the bot by using the "Learn" buttons in the Welcome Letter Bot

### "PDF generation failed" error
- PDF creation libraries (PyPDF2, reportlab) are not installed
- Run `INSTALL_BOTS.bat` again
- Or manually install: `pip install PyPDF2 reportlab`

### "Selenium not found" error
- Web automation libraries are not installed
- Run `INSTALL_BOTS.bat` again
- Or manually install: `pip install selenium webdriver-manager`

### Bot can't find buttons/coordinates
- Coordinate training data is missing
- Re-train the bot using the F9 hotkey (coordinate capture) or F8 hotkey (screenshot capture)
- Or copy the `*_coordinates.json` file from the source computer

## Quick Checklist

- [ ] Copied entire `_bots` folder to new computer
- [ ] Ran `INSTALL_BOTS.bat` successfully
- [ ] Copied `learned_pn_selectors.json` to `Documents\ISWS Welcome\` (if exists)
- [ ] Ran `VERIFY_BOT_CONFIGURATION.bat` to check files
- [ ] Tested each bot to ensure it starts
- [ ] Verified user credentials are present (or added new ones)
- [ ] Verified coordinate training data is present (or re-trained)

## Notes

- Configuration files are stored as JSON (plain text)
- User credentials are stored in plain text - keep these files secure!
- Each employee should have their own installation to maintain separate credentials
- If configuration files are missing, bots will create empty ones on first run
- You'll need to re-enter users and re-train coordinates if files are missing

