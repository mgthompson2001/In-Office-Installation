# Referral Document Cleanup Bot

This bot automatically cleans up old documents (30+ days) from Therapy Notes "New Referrals" patient groups.

## Features

- Reads counselors from an Excel file
- Logs into Therapy Notes (Base or IPS mode)
- Searches for each counselor's "{Counselor Name} New Referrals" patient group
- Automatically removes documents that are 30+ days old
- Provides detailed logging of all operations

## Installation

1. **Install Python 3.8 or higher** (if not already installed)
   - Download from https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the bot**
   - Double-click `referral_document_cleanup_bot.bat` or
   - Run `python referral_document_cleanup_bot.py` from the command line

## Usage

1. **Login to Therapy Notes**
   - Select mode: Base or IPS
   - Enter your Therapy Notes username and password
   - Click "Login to Therapy Notes"
   - Wait for login confirmation in the log

2. **Select Excel File**
   - Click "Browse..." to select your counselors Excel file
   - The Excel file should contain counselor names in a column
   - Common column names: "Counselor", "Therapist", "Name", "Provider"
   - Counselor names can be in "Last, First" format (e.g., "Smith, John") or "First Last" format

3. **Start Cleanup**
   - Click "Start Cleanup" button
   - The bot will:
     - Read all counselors from the Excel file
     - For each counselor, search for "{Counselor Name} New Referrals"
     - Open the Documents tab
     - Remove all documents that are 30+ days old
   - Monitor progress in the log window

## Excel File Format

The Excel file should contain counselor names in one of the columns. The bot will automatically detect columns with names like:
- "Counselor"
- "Therapist"
- "Name"
- "Provider"

If no such column is found, the first column will be used.

**Counselor Name Formats Supported:**
- "Last, First" (e.g., "Smith, John")
- "First Last" (e.g., "John Smith")
- "Last, First - IPS" (IPS indicator will be stripped)

**Important Notes:**
- In Base mode, counselors with "IPS" in their name will be skipped
- In IPS mode, counselors without "IPS" in their name will be skipped
- The bot searches for "{First Last} New Referrals" (e.g., "John Smith New Referrals")

## Saved Users

You can save multiple Therapy Notes user credentials:
1. Enter username and password
2. Click "Add User"
3. Enter a name for the user (e.g., "Admin Account")
4. Click "Save"

To use a saved user:
1. Select the user from the "Saved User" dropdown
2. Credentials will be automatically filled
3. Click "Login to Therapy Notes"

To update credentials:
1. Select the user from the dropdown
2. Modify the username/password
3. Click "Update"

## How It Works

1. **Search for Counselor**: The bot searches for "{Counselor Name} New Referrals" in Therapy Notes patient search
2. **Open Documents Tab**: Once the patient group is selected, the bot opens the Documents tab
3. **Find Old Documents**: The bot scans all documents in the table and identifies those with dates older than 30 days
4. **Delete Documents**: For each old document, the bot:
   - Clicks the pencil icon (edit button)
   - Clicks "Delete Document"
   - Clicks "Delete File" button
   - Confirms deletion

## Troubleshooting

**Login fails:**
- Verify your username and password are correct
- Make sure you're using the correct mode (Base vs IPS)
- Check your internet connection

**Excel file not loading:**
- Make sure the file is a valid Excel file (.xlsx or .xls)
- Verify the file is not open in another program
- Check that pandas and openpyxl are installed: `pip install pandas openpyxl`

**Counselor not found:**
- Verify the counselor name in Excel matches the format in Therapy Notes
- Check that the "New Referrals" patient group exists for that counselor
- The bot searches for "{First Last} New Referrals" format

**Documents not being deleted:**
- Verify documents are actually 30+ days old
- Check the log for specific error messages
- Make sure you have permission to delete documents in Therapy Notes

## Version

Version 1.0.0 - Initial release

## Support

For issues or questions, check the log output for detailed error messages.

