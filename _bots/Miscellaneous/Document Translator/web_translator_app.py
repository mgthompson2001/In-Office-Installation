#!/usr/bin/env python3
"""
Document Translator Web Application
Web interface for document translation service
"""

from flask import Flask, render_template, request, send_file, jsonify, flash, redirect, url_for, Response
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import tempfile
from pathlib import Path
import sys
import traceback
import time

# Add the current directory to path to import the translator bot
sys.path.insert(0, str(Path(__file__).parent))

# Import necessary modules directly (avoid GUI dependencies)
import pdfplumber
import pytesseract
from PIL import Image
from docx import Document
from deep_translator import GoogleTranslator
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size (increased for large files)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Don't cache files

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Language codes (same as in the bot)
LANGUAGES = {
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW",
    "Japanese": "ja",
    "Korean": "ko",
    "Arabic": "ar",
    "Hindi": "hi",
    "Dutch": "nl",
    "Polish": "pl",
    "Turkish": "tr",
    "Vietnamese": "vi",
    "Thai": "th",
    "Greek": "el",
    "Hebrew": "he",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",
    "Czech": "cs",
    "Romanian": "ro",
    "Hungarian": "hu",
    "Bulgarian": "bg",
    "Croatian": "hr",
    "Serbian": "sr",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Ukrainian": "uk",
    "Indonesian": "id",
    "Malay": "ms",
    "Tagalog": "tl",
    "Swahili": "sw",
    "Urdu": "ur",
    "Bengali": "bn",
    "Tamil": "ta",
    "Telugu": "te",
    "Marathi": "mr",
    "Gujarati": "gu",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Punjabi": "pa"
}

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', languages=sorted(LANGUAGES.keys()))

@app.route('/translate', methods=['GET', 'POST'])
def translate():
    """Handle document translation (POST) or redirect (GET)"""
    if request.method == 'GET':
        # If someone tries to access /translate directly, redirect to home
        flash('Please use the form on the home page to translate documents.', 'info')
        return redirect(url_for('index'))
    
    # Handle POST request
    try:
        translator = None
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        language = request.form.get('language')
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        if not language or language not in LANGUAGES:
            flash('Please select a target language', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload PDF, Word, or text files only.', 'error')
            return redirect(url_for('index'))
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        
        # Create output filename
        file_ext = Path(filename).suffix
        lang_code = LANGUAGES[language]
        
        # Check if user provided custom filename
        custom_filename = request.form.get('outputFilename', '').strip()
        if custom_filename:
            # Use custom filename, but ensure it has the correct extension
            if not custom_filename.endswith(file_ext):
                output_filename = custom_filename + file_ext
            else:
                output_filename = custom_filename
            # Sanitize filename
            output_filename = secure_filename(output_filename)
        else:
            # Auto-generate filename
            output_filename = f"{Path(filename).stem}_{lang_code}{file_ext}"
        
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # Check file size and warn if very large
        file_size = os.path.getsize(input_path)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb > 50:
            flash(f'Large file detected ({file_size_mb:.1f}MB). Processing may take several minutes. Please be patient.', 'info')
        
        # Import the translator class and create a headless instance
        try:
            from document_translator_bot import DocumentTranslatorBot
            
            # Create translator instance (with error handling for Tkinter)
            try:
                translator = DocumentTranslatorBot()
                
                # Hide the GUI window (headless mode)
                try:
                    translator.root.withdraw()
                except:
                    pass  # GUI might not be available in web context
            except Exception as init_err:
                print("=" * 70)
                print("ERROR INITIALIZING TRANSLATOR:")
                print("=" * 70)
                traceback.print_exc()
                print("=" * 70)
                flash(f'Error initializing translator: {str(init_err)[:100]}', 'error')
                return redirect(url_for('index'))
            
            # Disable GUI logging for web (reduce overhead for large files)
            if hasattr(translator, 'gui_log'):
                original_gui_log = translator.gui_log
                def quiet_log(msg):
                    # Only log important messages to reduce overhead
                    if any(keyword in msg.lower() for keyword in ['error', 'failed', 'complete', 'success']):
                        print(f"[WEB] {msg}")
                translator.gui_log = quiet_log
            
            # Set paths and language
            translator.input_file_path = input_path
            translator.output_file_path = output_path
            translator.language_var.set(language)
            
            # Read and translate document
            file_ext_lower = file_ext.lower()
            
            try:
                if file_ext_lower == '.pdf':
                    text = translator._read_pdf(input_path)
                elif file_ext_lower in ['.docx', '.doc']:
                    text = translator._read_docx(input_path)
                    # Check if Word document structure was captured
                    has_structure = hasattr(translator, 'docx_structure') and translator.docx_structure
                    if not has_structure:
                        print("[WEB] Warning: Word document structure not fully captured, using simple mode")
                elif file_ext_lower == '.txt':
                    text = translator._read_text_file(input_path)
                else:
                    if translator:
                        try:
                            translator.root.destroy()
                        except:
                            pass
                    flash('Unsupported file type', 'error')
                    return redirect(url_for('index'))
            except Exception as read_err:
                print("=" * 70)
                print("ERROR READING DOCUMENT:")
                print("=" * 70)
                traceback.print_exc()
                print("=" * 70)
                if translator:
                    try:
                        translator.root.destroy()
                    except:
                        pass
                flash(f'Error reading document: {str(read_err)[:100]}', 'error')
                return redirect(url_for('index'))
            
            if not text or not text.strip():
                if translator:
                    try:
                        translator.root.destroy()
                    except:
                        pass
                flash('No text could be extracted from the document', 'error')
                return redirect(url_for('index'))
            
            target_lang_code = LANGUAGES[language]
            
            # Translate
            try:
                if file_ext_lower == '.pdf' and PYMUPDF_AVAILABLE and hasattr(translator, 'pdf_text_blocks') and translator.pdf_text_blocks:
                    # Use block-by-block translation for PDFs
                    translator._translate_pdf_blocks(target_lang_code, output_path)
                else:
                    # Translate text normally
                    translated_text = translator._translate_text(text, target_lang_code)
                    
                    # Save translated document
                    if file_ext_lower == '.pdf':
                        translator._save_translated_pdf(translated_text, output_path)
                    elif file_ext_lower in ['.docx', '.doc']:
                        # Check if we have structure for advanced formatting
                        if hasattr(translator, 'docx_structure') and translator.docx_structure:
                            try:
                                translator._save_translated_docx_with_formatting(output_path)
                            except Exception as format_err:
                                print("=" * 70)
                                print("ERROR SAVING WITH FORMATTING (falling back to simple mode):")
                                print("=" * 70)
                                traceback.print_exc()
                                print("=" * 70)
                                # Fallback to simple saving
                                translator._save_translated_docx(translated_text, output_path)
                        else:
                            # Simple mode without structure
                            translator._save_translated_docx(translated_text, output_path)
                    else:
                        translator._save_translated_text(translated_text, output_path)
            except Exception as save_err:
                print("=" * 70)
                print("ERROR SAVING TRANSLATED DOCUMENT:")
                print("=" * 70)
                traceback.print_exc()
                print("=" * 70)
                if translator:
                    try:
                        translator.root.destroy()
                    except:
                        pass
                flash(f'Error saving translated document: {str(save_err)[:100]}', 'error')
                return redirect(url_for('index'))
        except Exception as translate_error:
            # Log the error for debugging
            error_details = str(translate_error)
            print("=" * 70)
            print("TRANSLATION ERROR:")
            print("=" * 70)
            traceback.print_exc()
            print("=" * 70)
            
            # Clean up translator on error
            if translator:
                try:
                    translator.root.destroy()
                except:
                    pass
            
            # User-friendly error messages
            if "tkinter" in error_details.lower() or "gui" in error_details.lower():
                flash('Server error: Please restart the server and try again.', 'error')
            elif "translation" in error_details.lower() or "google" in error_details.lower() or "api" in error_details.lower():
                flash('Translation service error. Please check your internet connection.', 'error')
            elif "file" in error_details.lower() or "not found" in error_details.lower():
                flash('File processing error. Please try a different file.', 'error')
            else:
                flash(f'Error: {error_details[:150]}', 'error')
            
            return redirect(url_for('index'))
        finally:
            # Clean up translator
            if translator:
                try:
                    translator.root.destroy()
                except:
                    pass
        
        # Return translated file for download
        # Use chunked response for large files to prevent memory issues
        def generate_file():
            with open(output_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # Read in 8KB chunks
                    if not chunk:
                        break
                    yield chunk
        
        # Check file size for chunked response
        file_size = os.path.getsize(output_path)
        if file_size > 10 * 1024 * 1024:  # If larger than 10MB, use chunked response
            response = Response(generate_file(), mimetype='application/octet-stream')
            response.headers['Content-Disposition'] = f'attachment; filename="{output_filename}"'
            response.headers['Content-Length'] = str(file_size)
            return response
        else:
            return send_file(
                output_path,
                as_attachment=True,
                download_name=output_filename,
                mimetype='application/octet-stream'
            )
        
    except Exception as e:
        # Outer exception handler for any other errors
        error_msg = str(e)
        print("=" * 70)
        print("FATAL ERROR:")
        print("=" * 70)
        traceback.print_exc()
        print("=" * 70)
        
        # Clean up translator
        if translator:
            try:
                translator.root.destroy()
            except:
                pass
        
        flash(f'Server error: {error_msg[:150]}. Check server console for details.', 'error')
        return redirect(url_for('index'))

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handle file size too large error"""
    flash('File is too large. Maximum file size is 200MB. Please try a smaller file.', 'error')
    return redirect(url_for('index'))

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    import socket
    
    # Get local IP address
    def get_local_ip():
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
    
    local_ip = get_local_ip()
    
    print("=" * 70)
    print("Document Translator Web Application")
    print("=" * 70)
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print()
    print("LOCAL ACCESS:")
    print(f"  http://localhost:5000")
    print()
    print("SHARE THIS LINK WITH OTHERS ON YOUR NETWORK:")
    print(f"  http://{local_ip}:5000")
    print()
    print("=" * 70)
    print("Server starting... Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)

