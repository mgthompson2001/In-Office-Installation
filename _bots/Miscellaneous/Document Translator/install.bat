@echo off
echo ========================================
echo Document Translator Bot - Installation
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo Python found. Installing dependencies...
echo.

REM Upgrade pip
python -m pip install --upgrade pip

REM Install requirements
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Some dependencies failed to install
    echo Please check the error messages above
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Note: For OCR functionality, you also need:
echo   1. Tesseract OCR - https://github.com/tesseract-ocr/tesseract/wiki
echo   2. Poppler for Windows - https://github.com/oschwartz10612/poppler-windows/releases/
echo.
echo See OCR_SETUP.md for detailed instructions.
echo.
pause

