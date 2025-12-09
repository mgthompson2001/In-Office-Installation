# Medicare Modifier Comparison Bot

This bot compares two Excel files to identify modifier mismatches that need refiling for Medicare claims.

## Overview

The bot matches records between two Excel files based on:
- **Name** (client/patient name)
- **DOB** (date of birth)
- **Date of Service**

Then it compares:
- **Session Medium** (from File 1, Column F) - indicates whether the session was video, phone, or in-person
- **Modifier** (from File 2, Column G) - the actual modifier on the claim

The bot determines which modifiers need refiling based on the session medium:
- **Video/Telehealth** → Should have modifier **95**
- **Phone/Telephone** → Should have modifier **93**
- **In-Person/Office** → Should have **no modifier**

## Usage

1. **Install dependencies**: Double-click `install.bat`
2. **Run the bot**: Double-click `medicare_modifier_comparison_bot.py` or `medicare_modifier_comparison_bot.bat`
3. **Select File 1**: Browse for the "Refile Medicare Log" Excel file (contains Session Medium in Column F)
4. **Select File 2**: Browse for the "Scrape Excel" file (contains Modifiers in Column G)
5. **Select Output Location**: Choose where to save the comparison results
6. **Click "Compare and Generate Output"**

## Input Files

### File 1: Refile Medicare Log
- **Column F**: Session Medium (Video, Phone, In-Person, etc.)
- Should contain: Name, DOB, Date of Service columns

### File 2: Scrape Excel
- **Column G**: Modifier (95, 93, or blank)
- Should contain: Name, DOB, Date of Service columns

## Output

The output Excel file contains:
- **Name**, **DOB**, **Date_of_Service**: Matching fields
- **Session_Medium**: From File 1
- **Expected_Modifier**: What modifier should be based on session medium
- **Actual_Modifier**: What modifier is actually on the claim (from File 2)
- **Needs_Refile**: Yes/No indicator
- **Refile_Reason**: Explanation of why refiling is needed
- **Match_Status**: Whether a match was found between the two files
- All other columns from both input files

## Requirements

- Python 3.7+
- pandas
- openpyxl

