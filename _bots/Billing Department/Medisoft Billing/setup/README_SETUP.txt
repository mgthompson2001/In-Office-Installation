Medisoft Bot - OCR Dependencies Setup (Windows)

This bot uses OCR for scanned PDFs. Two dependencies are required:
- Tesseract OCR (for text extraction)
- Poppler (for PDF-to-image conversion)

Quick Setup (Recommended):
1) Right-click install_ocr.ps1 and choose "Run with PowerShell".
   - If winget is available, it will install Tesseract/Poppler automatically.
   - If winget is not available, it will download a portable Poppler into vendor\poppler.
2) Restart your terminal or log out/in to apply environment changes.

Manual Setup (if needed):
- Tesseract OCR:
  - Install: winget install -e --id UB-Mannheim.TesseractOCR
  - Or download from: https://github.com/tesseract-ocr/tesseract/wiki
  - Set environment variable (User): TESSERACT_PATH = C:\Program Files\Tesseract-OCR\tesseract.exe

- Poppler:
  - Install: winget install -e --id Poppler.Poppler (if available)
  - Or download a Windows build: https://github.com/oschwartz10612/poppler-windows/releases
  - Set environment variable (User): POPPLER_PATH = <path to Poppler>\Library\bin

How it works at runtime:
- The bot auto-detects paths in this order:
  1) TESSERACT_PATH and POPPLER_PATH environment variables
  2) vendor\Tesseract-OCR\tesseract.exe and vendor\poppler\Library\bin
  3) Common install locations (Program Files, LocalAppData, Conda)

If OCR still fails:
- Verify the paths exist
- Ensure POPPLER_PATH contains pdftoppm.exe
- Re-run setup or set env vars manually
