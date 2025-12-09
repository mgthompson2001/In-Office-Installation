# OCR Setup Instructions for Scanned PDFs

The bot can extract text from scanned PDFs (image-based PDFs) using OCR (Optical Character Recognition).

## Required Components

For OCR to work, you need **three components**:

### 1. Python Packages (Auto-installed via `install.bat`)
- `pdf2image` - Converts PDF pages to images
- `pytesseract` - Python wrapper for Tesseract OCR
- `Pillow` - Image processing (usually already installed)

These are automatically installed when you run `install.bat`.

### 2. Poppler for Windows (REQUIRED)
`pdf2image` needs Poppler to convert PDF pages to images.

**Download and Install:**
1. Download Poppler for Windows from: https://github.com/oschwartz10612/poppler-windows/releases/
2. Download the latest `.zip` file (e.g., `Release-XX.XX.X-0.zip`)
3. Extract the ZIP file to a folder (e.g., `C:\poppler`)
4. Add the `bin` folder to your Windows PATH:
   - Right-click "This PC" → Properties → Advanced system settings
   - Click "Environment Variables"
   - Under "System variables", find and select "Path", then click "Edit"
   - Click "New" and add the path to Poppler's `bin` folder (e.g., `C:\poppler\Library\bin`)
   - Click OK on all dialogs
   - **Restart your terminal/command prompt** for changes to take effect

**Quick Test:**
Open a new command prompt and type: `pdftoppm -h`
If it shows help text, Poppler is installed correctly!

### 3. Tesseract OCR (REQUIRED)
Tesseract OCR performs the actual text recognition.

**Download and Install:**
1. Download Tesseract OCR for Windows from: https://github.com/tesseract-ocr/tesseract/wiki
2. Choose the Windows installer (e.g., `tesseract-ocr-w64-setup-5.X.X.exe`)
3. Run the installer
4. **Important:** During installation, check "Add to PATH" if available
   - Or manually add `C:\Program Files\Tesseract-OCR` to your PATH (same steps as Poppler above)
5. **Restart your terminal/command prompt**

**Quick Test:**
Open a new command prompt and type: `tesseract --version`
If it shows the version, Tesseract is installed correctly!

## Verification

After installing both, test the OCR functionality:

```bash
cd "C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\_bots\Billing Department\Medisoft Billing"
python test_bot_pdf.py
```

If OCR is working, you should see:
- "OCR extraction completed" message
- Extracted text from the PDF
- "Sean Hansen" and date range successfully extracted

## Troubleshooting

**Error: "Unable to get page count. Is poppler installed and in PATH?"**
- Poppler is not installed or not in PATH
- Reinstall Poppler and ensure PATH is set correctly
- Restart your terminal/command prompt

**Error: "tesseract is not installed or it's not in your PATH"**
- Tesseract OCR is not installed or not in PATH
- Reinstall Tesseract and ensure PATH is set correctly
- Restart your terminal/command prompt

**Still not working?**
1. Verify both are in PATH: Open new command prompt and test `pdftoppm -h` and `tesseract --version`
2. Try restarting your computer
3. Make sure you're using a new terminal/command prompt (PATH changes require restart)

## Alternative: Use Text-Based PDFs

If OCR setup is too complex, you can use text-based PDFs (PDFs that have selectable text):
- These PDFs don't require OCR
- The bot will extract text directly using `pdfplumber`
- Most modern PDFs from insurance companies are text-based

