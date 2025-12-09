# Visual PDF Field Mapper Guide

## Overview

The Visual PDF Field Mapper provides an interactive, graphical interface for configuring PDF form fields. Instead of manually editing configuration files, you can:

1. **See the PDF** - Visual preview of your PDF form
2. **Click fields** - Click on any form field to configure it
3. **Save selectors** - Save your configuration for future use
4. **Persistent storage** - Your settings are saved and loaded automatically

## Features

### ✅ Visual PDF Preview
- Full PDF page display with high-quality rendering
- Multi-page support with page navigation
- Zoom in/out controls
- Scrollable canvas for large PDFs

### ✅ Clickable Field Regions
- All form fields are highlighted with colored rectangles
- **Green rectangles** = Configured fields (will be filled)
- **Yellow rectangles** = Unconfigured fields (will be left blank)
- Hover over fields to see field names
- Click on any field to configure it

### ✅ Field Configuration Dialog
When you click a field, a dialog appears where you can:
- **Enable/Disable** the field
- **Choose data source**: Excel column or static value
- **Select Excel column** (for Excel data source)
- **Enter static value** (for static data source)

### ✅ Save Selectors
- Click "Save Selectors" to save your configuration
- Configuration is saved to `pdf_field_mapping_config.json`
- Settings are automatically loaded when you reopen the bot
- Your custom field mappings persist across sessions

## How to Use

### Step 1: Select PDF Template
1. Go to the "PDF Forms" tab
2. Click "Browse..." to select your PDF template
3. Wait for the PDF to load (fields will be detected automatically)

### Step 2: Open Visual Mapper
1. Click "Visual Field Mapper" button
2. The PDF will be displayed with field rectangles overlaid

### Step 3: Configure Fields
1. **Click on a field** you want to configure
2. In the configuration dialog:
   - Check "Enable this field"
   - Choose "excel" or "static" as data source
   - Select Excel column (if "excel") or enter static value (if "static")
   - Click "Save"

3. **Repeat** for all fields you want to fill

### Step 4: Save Selectors
1. Click "Save Selectors" button
2. Your configuration is saved to the config file
3. Settings will be automatically loaded next time you open the bot

### Step 5: Use Configuration
1. Select your audit results Excel file
2. Select output folder
3. Click "Start Filling PDFs"
4. The bot will use your saved field selectors to fill the PDFs

## Field Configuration Options

### Excel Data Source
Select "excel" to fill the field with data from your audit Excel file.

Available Excel columns:
- `client_name` - Client name
- `first_name` - First name
- `last_name` - Last name
- `dob` - Date of birth
- `dos` - Date of service
- `patient_member_id` - Patient Member # (MBI)
- `session_medium` - Session medium (PHONE/VIDEO)
- `original_modifier` - Original modifier from TherapyNotes
- `expected_modifier` - Expected modifier (93 or 95)
- `status` - Audit status
- `notes` - Audit notes

### Static Data Source
Select "static" to fill the field with a fixed value (same for all clients).

Example uses:
- Provider Name
- NPI Number
- PTAN Number
- Tax ID
- Provider Address

## Visual Indicators

### Field Colors
- **Green** = Field is configured and enabled
- **Yellow** = Field is not configured (will be left blank)

### Status Messages
- **Hover over field** = Shows field name and configuration status
- **Click field** = Opens configuration dialog
- **Status bar** = Shows current status and instructions

## Tips

1. **Configure all fields at once** - Set up all fields, then click "Save Selectors" once
2. **Use Excel for patient data** - Use "excel" data source for fields that vary per client
3. **Use static for provider info** - Use "static" data source for fields that are the same for all clients
4. **Disable unused fields** - Fields that are not enabled will be left blank
5. **Save frequently** - Click "Save Selectors" to save your progress

## Troubleshooting

### PDF Not Displaying
- Make sure PyMuPDF (fitz) is installed: `pip install PyMuPDF`
- Make sure PIL/Pillow is installed: `pip install Pillow`
- Check that the PDF file is not corrupted

### Fields Not Clickable
- Make sure the PDF has fillable form fields
- Try zooming in/out to adjust field positions
- Check that field rectangles are visible (yellow/green highlights)

### Configuration Not Saving
- Check that you clicked "Save Selectors" button
- Check the Activity Log for error messages
- Verify that the config file is writable

## Configuration File

Your field selectors are saved to:
```
pdf_field_mapping_config.json
```

This file is automatically created and updated when you save selectors. You can also edit this file manually if needed, but the visual mapper is recommended.

## Example Workflow

1. **Select PDF template**: `1939_072519_b_reopening_request_508.pdf`
2. **Open Visual Mapper**: Click "Visual Field Mapper"
3. **Configure Beneficiary's Name**: Click field → Enable → Excel → `client_name` → Save
4. **Configure Date of Birth**: Click field → Enable → Excel → `dob` → Save
5. **Configure MBI**: Click field → Enable → Excel → `patient_member_id` → Save
6. **Configure NPI**: Click field → Enable → Static → `1234567890` → Save
7. **Save Selectors**: Click "Save Selectors"
8. **Close Visual Mapper**: Click "Close"
9. **Fill PDFs**: Select audit Excel → Select output folder → Click "Start Filling PDFs"

## Next Steps

After configuring your fields:
1. Run the audit workflow to generate the audit results Excel
2. Use the "PDF Forms" tab to fill PDFs for clients who "Need Refile"
3. The bot will use your saved field selectors to fill the PDFs automatically

