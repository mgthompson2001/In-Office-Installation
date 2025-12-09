# Document Translator Bot

A powerful tool for translating documents (PDF, Word, text files) to any language using OCR and translation services.

## Features

- **Multiple Format Support**: PDF, Word documents (.docx, .doc), and plain text files
- **OCR Capability**: Automatically detects and processes scanned PDFs using OCR
- **50+ Languages**: Translate to over 50 languages including Spanish, French, German, Chinese, Japanese, and more
- **Smart Text Extraction**: Handles both text-based and scanned documents
- **Preserves Format**: Maintains document structure when possible

## Quick Start

1. **Install dependencies**: Double-click `install.bat`
2. **Run the bot**: Double-click `document_translator_bot.bat`
3. **Select document**: Click "Browse..." to select your input document
4. **Choose language**: Click "Select Language" to choose target language
5. **Translate**: Click "Translate Document"

## Requirements

### Python Packages (Auto-installed)
- `pdfplumber` - PDF text extraction
- `pytesseract` - OCR text recognition
- `pdf2image` - PDF to image conversion for OCR
- `python-docx` - Word document reading/writing
- `deep-translator` - Translation service
- `reportlab` - PDF creation (optional)

### External Software (For OCR)

**Tesseract OCR** (Required for scanned PDFs):
1. Download from: https://github.com/tesseract-ocr/tesseract/wiki
2. Install and add to PATH
3. Test: `tesseract --version`

**Poppler** (Required for OCR):
1. Download from: https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract and add `bin` folder to PATH
3. Test: `pdftoppm -h`

See `OCR_SETUP.md` for detailed installation instructions.

## Supported Languages

The bot supports translation to 50+ languages including:
- Spanish, French, German, Italian, Portuguese
- Chinese (Simplified & Traditional), Japanese, Korean
- Arabic, Hindi, Russian, and many more

See the language selection dialog in the bot for the complete list.

## Usage

1. **Select Input Document**: Choose a PDF, Word document, or text file
2. **Select Target Language**: Use the language selection dialog to choose your target language
3. **Choose Output Location** (optional): Defaults to same folder as input with language suffix
4. **Translate**: Click "Translate Document" and wait for processing

The bot will:
- Extract text from your document (using OCR if needed for scanned PDFs)
- Translate the text to your selected language
- Save the translated document in the same format (or text file if PDF creation fails)

## Notes

- **Large Documents**: Very large documents may take several minutes to process
- **OCR Processing**: Scanned PDFs require OCR which can be slow for multi-page documents
- **Translation Quality**: Uses Google Translate API (via deep-translator) for reliable translations
- **Format Preservation**: PDF formatting may be simplified in the output; Word documents preserve paragraph structure

## Troubleshooting

**"pdfplumber not available"**
- Run `install.bat` to install dependencies

**"OCR not available"**
- Install Tesseract OCR and Poppler (see Requirements above)
- Ensure both are added to your system PATH

**"Translation failed"**
- Check your internet connection (translation requires online service)
- Try again - Google Translate may have temporary rate limits

**"No text extracted"**
- For scanned PDFs, ensure OCR is properly installed
- Try a different document to verify the bot is working

## File Structure

```
Document Translator/
├── document_translator_bot.py    # Main application
├── document_translator_bot.bat   # Launcher script
├── install.bat                   # Installation script
├── requirements.txt              # Python dependencies
├── README.md                     # This file
└── document_translator.log       # Log file (auto-created)
```

