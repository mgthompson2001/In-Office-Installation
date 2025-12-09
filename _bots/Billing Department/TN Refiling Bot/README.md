# TN Refiling Bot

Automated bot for refiling claims in Therapy Notes. This bot reads client data from Excel/CSV files and searches for clients using DOB, name, and date of service. It can also extract claim numbers from scanned PDF documents using OCR.

## Features

- **PDF/OCR Capabilities**: Extract claim numbers from scanned PDF documents using Tesseract OCR and Poppler
- **Excel/CSV Reading**: Read complex Excel/CSV files containing client data (Name, DOB, Date of Service)
- **User Management**: Save and manage multiple user credentials securely
- **GUI Interface**: Easy-to-use graphical interface with real-time activity logging
- **Therapy Notes Integration**: (To be implemented) Automated login and client search in Therapy Notes

## Installation

### 1. Install Python Dependencies

Run the installation script or manually install requirements:

```bash
pip install -r requirements.txt
```

### 2. Install OCR Dependencies

The bot requires two additional components for PDF OCR:

#### Tesseract OCR
1. Download from: https://github.com/tesseract-ocr/tesseract/wiki
2. Run the installer
3. Add `C:\Program Files\Tesseract-OCR` to your PATH (or set `TESSERACT_PATH` environment variable)

#### Poppler
1. Download from: https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract the ZIP file
3. Add the `bin` folder to your PATH (or set `POPPLER_PATH` environment variable)

## Usage

### Running the Bot

1. Double-click `tn_refiling_bot.py` or run from command line:
   ```bash
   python tn_refiling_bot.py
   ```

2. **Add User Credentials**:
   - Click "Add User" to create a new user profile
   - Enter a user name, username, and password for Therapy Notes
   - Credentials are saved locally in `tn_users.json`

3. **Select User or Enter Credentials**:
   - Select a saved user from the dropdown (auto-fills credentials)
   - Or manually enter username and password

4. **Extract Claim Numbers from PDF**:
   - Click "Browse..." to select a scanned PDF document
   - Click "Extract Claim #" to extract the claim number using OCR
   - The extracted claim number will be displayed

5. **Load Client Data from Excel/CSV**:
   - Click "Browse..." or "Paste path..." to load an Excel/CSV file
   - The bot will automatically identify columns (Name, DOB, Date of Service)
   - A preview of loaded clients will be displayed

### Excel/CSV File Format

The bot automatically detects columns with these common names:
- **Name**: "Last Name", "First Name", "Patient Name", "Client Name", "Name"
- **DOB**: "DOB", "Date of Birth", "Birth Date", "Birthdate"
- **Date of Service**: "Date", "Service Date", "Date of Service", "DOS", "Appointment Date"

If your file uses different column names, ensure they contain similar keywords.

## File Structure

```
TN Refiling Bot/
├── tn_refiling_bot.py    # Main application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── tn_users.json         # Saved user credentials (auto-created)
└── tn_coordinates.json   # Saved coordinates (auto-created)
```

## Security

- All credentials are stored **locally** on your computer
- Credentials are saved in `tn_users.json` (plain text - keep secure!)
- Never share your `tn_users.json` file
- Each user maintains their own installation

## Troubleshooting

**Bot won't start?**
- Run `pip install -r requirements.txt` to ensure all dependencies are installed
- Check that Python is installed: Open Command Prompt, type `python --version`

**PDF OCR not working?**
- Verify Tesseract OCR is installed: Open Command Prompt, type `tesseract --version`
- Verify Poppler is installed: Open Command Prompt, type `pdftoppm -h`
- Check environment variables `TESSERACT_PATH` and `POPPLER_PATH` are set correctly

**Excel/CSV not loading?**
- Ensure the file is not open in Excel
- Check that column names contain keywords (Name, DOB, Date of Service)
- Verify the file is in `.xlsx`, `.xls`, or `.csv` format

## Future Enhancements

The following features are planned for future development:
- Therapy Notes login automation
- Automated client search in Therapy Notes using loaded data
- Automated claim refiling workflow
- Batch processing for multiple clients

## Notes

- The bot is designed to work incrementally - we'll build additional features as we understand the Therapy Notes workflow better
- PDF OCR works best with high-quality scanned documents
- The bot uses image recognition and coordinate-based automation similar to the Medisoft bot

