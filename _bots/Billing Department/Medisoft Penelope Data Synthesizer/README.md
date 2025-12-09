# Medisoft/Penelope Data Synthesizer

This bot synthesizes data from a PDF report and an Excel spreadsheet to create a combined output Excel document.

## Overview

The bot matches records based on:
- **Chart column** from the PDF report
- **PT code (Column E)** from the Excel file

It then combines all relevant information from both sources into a single output Excel file.

## Features

- Extracts data from PDF reports using table extraction
- Reads Excel files with support for Penelope ID, DOB, and other columns
- Matches records automatically based on Chart value (PDF) and PT code (Excel)
- Combines all matching information including:
  - Date of Service (from PDF)
  - Penelope ID (from Excel)
  - DOB (from Excel)
  - Modifiers, Counselor Names, Supervisor (from PDF)
  - All other available fields from both sources

## Usage

1. **Launch the bot** from the Billing Department launcher
2. **Select PDF Report**: Browse and select the PDF file containing transaction data
3. **Select Excel File**: Browse and select the Excel file containing client data
4. **Select Output Location**: Choose where to save the synthesized Excel file (or let it auto-generate)
5. **Click "Synthesize Data"**: The bot will process both files and create the output

## Requirements

- Python 3.7+
- pandas
- openpyxl
- pdfplumber

Install dependencies with:
```bash
pip install -r requirements.txt
```

## Expected Input Formats

### PDF Report
- Should contain a table with a "Chart" column
- Date of Service, Modifier, Counselor Name, Supervisor, and other fields should be in separate columns

### Excel File
- **Column E** should contain PT codes (used for matching)
- Should contain a Penelope ID column (will be auto-detected)
- Should contain a DOB column (will be auto-detected)
- All other columns will be included in the output

## Output Format

The output Excel file contains:
- All fields from the PDF (prefixed with "PDF_")
- All fields from the Excel file (prefixed with "Excel_")
- Key matching fields prominently displayed:
  - Date_of_Service
  - Penelope_ID
  - DOB
  - Chart_Value
  - PT_Code
  - Modifier
  - Counselor_Name
  - Supervisor

## Notes

- The bot normalizes PT codes for matching (removes spaces, leading zeros)
- Unmatched records are logged but not included in the output
- The bot processes files in a separate thread to keep the UI responsive

