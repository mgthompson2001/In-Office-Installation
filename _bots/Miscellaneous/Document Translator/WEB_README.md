# Document Translator Web Application

A web-based interface for the Document Translator bot that allows users to upload documents and translate them online.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements_web.txt
   ```

2. **Run the web server:**
   - Double-click `run_web_server.bat` (Windows)
   - Or run: `python web_translator_app.py`

3. **Access the application:**
   - Open your web browser
   - Navigate to: `http://localhost:5000`

## Features

- **Web Interface**: Beautiful, modern web UI
- **File Upload**: Drag-and-drop or click to upload
- **Multiple Formats**: PDF, Word documents (.docx, .doc), and text files
- **50+ Languages**: Translate to over 50 languages
- **Layout Preservation**: Maintains document formatting (for PDFs)
- **OCR Support**: Handles scanned PDFs automatically

## Usage

1. Upload your document using the upload area
2. Select the target language from the dropdown
3. Click "Translate Document"
4. Download your translated document

## Deployment

### Local Network Access

To allow other devices on your network to access the web app:

1. Find your computer's IP address:
   - Windows: `ipconfig` (look for IPv4 Address)
   - Example: `192.168.1.100`

2. Modify `web_translator_app.py`:
   ```python
   app.run(debug=True, host='0.0.0.0', port=5000)
   ```
   (Already configured)

3. Access from other devices:
   - `http://YOUR_IP_ADDRESS:5000`
   - Example: `http://192.168.1.100:5000`

### Production Deployment

For production use, consider:

1. **Use a production WSGI server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 web_translator_app:app
   ```

2. **Use nginx as reverse proxy** (recommended for production)

3. **Add authentication** if needed

4. **Set up SSL/HTTPS** for secure connections

5. **Change the secret key** in `web_translator_app.py`:
   ```python
   app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
   ```

## File Structure

```
Document Translator/
├── web_translator_app.py      # Flask web application
├── templates/
│   └── index.html             # Web interface template
├── requirements_web.txt        # Web dependencies
├── run_web_server.bat         # Windows launcher
└── WEB_README.md              # This file
```

## Troubleshooting

**Port already in use:**
- Change the port in `web_translator_app.py`: `app.run(..., port=5001)`

**Files not uploading:**
- Check file size (max 50MB)
- Ensure file type is supported (.pdf, .docx, .doc, .txt)

**Translation fails:**
- Check internet connection (required for translation API)
- Verify all dependencies are installed
- Check the console for error messages

## Security Notes

- The web app currently has no authentication
- Files are stored temporarily and deleted after download
- For production use, add authentication and rate limiting
- Consider adding file size limits and virus scanning

