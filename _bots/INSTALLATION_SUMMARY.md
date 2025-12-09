# Bot Installation System - Summary of Changes

## What Was Fixed

Your bot installation system has been updated to ensure all dependencies and configuration files are properly installed and preserved when transferring to new computers.

## Files Created/Updated

### 1. **INSTALL_BOTS.bat** (UPDATED - Root Level)
   - **Location:** `In-Office Installation\INSTALL_BOTS.bat` (root folder)
   - **Purpose:** Master installation script that installs ALL dependencies for ALL bots
   - **Note:** This is the main installation script - use this one!
   - **What it installs:**
     - Core automation: pyautogui, pywinauto, Pillow, keyboard, pyperclip
     - PDF reading/parsing: pdfplumber, pdf2image, pytesseract
     - **PDF creation:** PyPDF2, reportlab, fpdf2 (NEW - fixes your issue!)
     - Data processing: pandas, openpyxl
     - Web automation: selenium, webdriver-manager (for Penelope & Welcome Letter bots)
     - Image recognition: opencv-python

### 2. **VERIFY_BOT_CONFIGURATION.bat** (NEW)
   - **Location:** `_bots\VERIFY_BOT_CONFIGURATION.bat`
   - **Purpose:** Verifies all bot configuration files are present
   - **What it checks:**
     - All `*_users.json` files (saved credentials)
     - All `*_coordinates.json` files (saved training data)
     - All `*_settings.json` files (bot settings)
     - Special file: `learned_pn_selectors.json` (Welcome Letter Bot selectors)

### 3. **BOT_CONFIGURATION_GUIDE.md** (NEW)
   - **Location:** `_bots\BOT_CONFIGURATION_GUIDE.md`
   - **Purpose:** Complete guide for transferring bots to new computers
   - **Contents:**
     - List of all configuration files by bot
     - Step-by-step installation instructions
     - Troubleshooting guide
     - Quick checklist

### 4. **requirements.txt** (UPDATED)
   - **Location:** `Billing Department\Medisoft Billing\requirements.txt`
   - **Added:**
     - PyPDF2>=3.0.0 (PDF reading/manipulation)
     - reportlab>=4.0.0 (PDF creation/generation)
     - fpdf2>=2.7.0 (Simple PDF creation)
     - selenium>=4.0.0 (Web automation)
     - webdriver-manager>=4.0.0 (Chrome driver management)

### 5. **install.bat** (UPDATED)
   - **Location:** `Billing Department\Medisoft Billing\install.bat`
   - **Added:** All PDF creation and web automation libraries to installation command

## How to Use on New Computer

### Step 1: Copy the Folder
Copy the entire `_bots` folder to the new computer, maintaining the folder structure.

### Step 2: Run Installation
Double-click `INSTALL_BOTS.bat` from the root `In-Office Installation` folder.

This will install:
- ✅ All Python dependencies
- ✅ PDF creation libraries (PyPDF2, reportlab, fpdf2)
- ✅ Web automation libraries (selenium, webdriver-manager)
- ✅ All other required packages

### Step 3: Verify Configuration
Double-click `VERIFY_BOT_CONFIGURATION.bat` to check that all configuration files are present.

### Step 4: Special File (Welcome Letter Bot)
If the Welcome Letter Bot was used on the source computer, copy:
- **From:** `Documents\ISWS Welcome\learned_pn_selectors.json` (on source computer)
- **To:** `Documents\ISWS Welcome\learned_pn_selectors.json` (on new computer)

Create the folder if it doesn't exist.

### Step 5: Test Bots
Run each bot to ensure everything works:
- Medisoft Billing Bot
- Penelope Workflow Tool
- Welcome Letter Bot
- Other bots as needed

## What's Preserved

When you copy the `_bots` folder, these are automatically preserved:
- ✅ User credentials (`*_users.json` files)
- ✅ Coordinate training data (`*_coordinates.json` files)
- ✅ Bot settings (`*_settings.json` files)
- ✅ Screenshot images (`.png` files)
- ✅ PDF field mappings (`pdf_field_mapping_config.json`)

⚠️ **Manual transfer required:**
- `learned_pn_selectors.json` (stored in Documents folder, not in bot folder)

## Dependencies Now Included

### PDF Libraries (NEW)
- **PyPDF2** - PDF reading and manipulation (used by Welcome Letter Bot)
- **reportlab** - PDF creation and generation (used by Welcome Letter Bot)
- **fpdf2** - Simple PDF creation (optional)

### Web Automation (NEW)
- **selenium** - Web browser automation (used by Penelope & Welcome Letter bots)
- **webdriver-manager** - Automatic Chrome driver management

### Existing Dependencies (Already Working)
- pdfplumber - PDF parsing
- pdf2image - PDF to image conversion
- pytesseract - OCR text extraction
- pyautogui, pywinauto - GUI automation
- pandas, openpyxl - Excel/CSV processing
- opencv-python - Image recognition

## Troubleshooting

### "Selectors not available" (Welcome Letter Bot)
- Copy `learned_pn_selectors.json` from source computer to `Documents\ISWS Welcome\`
- Or re-train the bot using the "Learn" buttons

### "PDF generation failed"
- Run `INSTALL_BOTS.bat` again
- Or manually: `pip install PyPDF2 reportlab`

### "Selenium not found"
- Run `INSTALL_BOTS.bat` again
- Or manually: `pip install selenium webdriver-manager`

## Next Steps

1. ✅ Test `INSTALL_BOTS.bat` on your current computer to verify it works
2. ✅ When transferring to a new computer, use the new installation process
3. ✅ Run `VERIFY_BOT_CONFIGURATION.bat` after installation
4. ✅ Refer to `BOT_CONFIGURATION_GUIDE.md` for detailed instructions

## Summary

Your installation system is now comprehensive and will:
- ✅ Install all dependencies including PDF creation libraries
- ✅ Preserve all bot memory (selectors, coordinates, users)
- ✅ Work for all bots in your system
- ✅ Provide verification tools to check configuration

The main issue (PDF dependencies not being installed) is now fixed!

