# Missed Appointments Tracker Bot

Automated bot for tracking missed appointments across 330+ counselors and thousands of clients by synthesizing data from Excel spreadsheets and Therapy Notes web application.

## Features

- **Excel Data Integration**: Loads active clients and counselors from Excel spreadsheets
- **Therapy Notes Navigation**: Automatically logs in and navigates Therapy Notes to extract document counts
- **Frequency Analysis**: Calculates expected sessions based on frequency (1x weekly, 2x monthly, etc.)
- **Missed Appointment Detection**: Compares expected vs actual sessions to identify potential missed appointments
- **Reassignment Handling**: Flags reassigned clients for manual review
- **Comprehensive Reporting**: Generates detailed Excel report of potential missed appointments

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the bot**:
   ```bash
   python missed_appointments_tracker_bot.py
   ```

## Usage

1. **Select Excel Files**:
   - Active Clients Excel: `ODBC NEW Client List.xlsx` (or similar)
   - Active Counselors Excel: `Master Counselor List.xlsx` (sheet: "ISWS Counselors")

2. **Enter Therapy Notes Credentials**:
   - URL: `https://www.therapynotes.com/app/login/IntegritySWS/`
   - Username and Password

3. **Set Date Range**:
   - Enter start and end dates in MM/DD/YYYY format
   - Example: 10/01/2024 to 10/31/2024

4. **Start Analysis**:
   - Click "Start Analysis"
   - The bot will process all clients and generate a report

## Excel File Requirements

### Clients Excel
Required columns:
- `Last_Name`: Client's last name
- `First_Name`: Client's first name
- `Counselor`: Counselor name (format: "Last, First")
- `Frequency`: Session frequency (e.g., "1x Weekly", "Every 2 Weeks", "Monthly")
- `New or Reassignment`: Reassignment status ("Reassignment", "New Case", or "---")
- `service_file_start_date`: Date when service file started (for reassignments)
- `DOB`: Date of birth (optional, for client matching)

### Counselors Excel
Required columns (sheet: "ISWS Counselors"):
- `Last Name`: Counselor's last name
- `First Name`: Counselor's first name
- `Date of Term`: Termination date (if applicable)

## Output Report

The bot generates an Excel file with the following columns:
- Client Name
- Counselor Name
- Date Range Start/End
- Expected Sessions
- Actual Sessions
- Missed Count
- Frequency
- Reassigned (Yes/No)
- Reassignment Date
- Reassignment Note (for manual review)
- Confidence Level (High/Medium/Low)
- Notes

## Notes

- **Counselor Client List Navigation**: Currently implemented as a placeholder. The bot searches for clients individually. This will be enhanced once the Therapy Notes navigation structure for counselor client lists is determined.

- **Reassigned Clients**: Clients marked as "Reassignment" or "New Case" are flagged with a note requiring manual review, as grace periods during reassignment may affect session counts.

- **Processing Time**: With 330+ counselors and thousands of clients, processing may take several hours. The bot includes progress tracking and can be stopped/resumed.

## Troubleshooting

**Browser issues?**
- Ensure Chrome is installed and up to date
- The bot uses ChromeDriver which is automatically managed by webdriver-manager

**Excel file errors?**
- Ensure Excel files are not open in another program
- Check that required columns exist in the files

**Therapy Notes login fails?**
- Verify credentials are correct
- Check that the URL is correct for your organization
- Ensure you have internet connectivity

## Future Enhancements

- [ ] Implement counselor client list navigation (currently placeholder)
- [ ] Add resume capability for interrupted runs
- [ ] Batch processing for better performance
- [ ] Enhanced document type detection
- [ ] Configurable grace period for reassignments

