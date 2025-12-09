@echo off
setlocal enabledelayedexpansion

REM ==============================================
REM  Tesseract OCR Installer
REM  Installs Tesseract OCR for PDF text extraction
REM ==============================================

echo.
echo ================================================
echo  Tesseract OCR Installation
echo ================================================
echo.
echo This script will install Tesseract OCR, which is required
echo for processing scanned PDFs in the Medisoft Billing Bot.
echo.
pause

REM Change to the root installation directory (parent of Installer folder)
cd /d "%~dp0.."

REM Check if Tesseract is already installed
set "TESSERACT_FOUND=0"
set "TESSERACT_PATH="

REM Check common installation locations
if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" (
    set "TESSERACT_PATH=%ProgramFiles%\Tesseract-OCR"
    set "TESSERACT_FOUND=1"
) else if exist "%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe" (
    set "TESSERACT_PATH=%ProgramFiles(x86)%\Tesseract-OCR"
    set "TESSERACT_FOUND=1"
) else if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" (
    set "TESSERACT_PATH=%LOCALAPPDATA%\Programs\Tesseract-OCR"
    set "TESSERACT_FOUND=1"
)

if "%TESSERACT_FOUND%"=="1" (
    echo [OK] Tesseract OCR is already installed at: !TESSERACT_PATH!
    echo.
    if not "%1"=="NO_PAUSE" (
        echo Tesseract is ready to use!
        echo.
        pause
    )
    exit /b 0
)

echo [INFO] Tesseract OCR not found - installing now...
echo.

REM Create vendor directory for portable installation (in root directory)
set "VENDOR_DIR=%~dp0..\vendor"
if not exist "%VENDOR_DIR%" mkdir "%VENDOR_DIR%"

REM Run PowerShell installer (use the correct script in Installer folder)
set "TESSERACT_SCRIPT=%~dp0install_ocr_dependencies.ps1"

if exist "%TESSERACT_SCRIPT%" (
    echo [INFO] Running Tesseract installer...
    cd /d "%~dp0.."
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TESSERACT_SCRIPT%" -InstallDir "%CD%"
    cd /d "%~dp0"
    
    REM Check again after installation
    if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" (
        set "TESSERACT_PATH=%ProgramFiles%\Tesseract-OCR"
        set "TESSERACT_FOUND=1"
    ) else if exist "%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe" (
        set "TESSERACT_PATH=%ProgramFiles(x86)%\Tesseract-OCR"
        set "TESSERACT_FOUND=1"
    ) else if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" (
        set "TESSERACT_PATH=%LOCALAPPDATA%\Programs\Tesseract-OCR"
        set "TESSERACT_FOUND=1"
    ) else if exist "%VENDOR_DIR%\Tesseract-OCR\tesseract.exe" (
        set "TESSERACT_PATH=%VENDOR_DIR%\Tesseract-OCR"
        set "TESSERACT_FOUND=1"
    )
)

if "%TESSERACT_FOUND%"=="1" (
    echo.
    echo [OK] Tesseract OCR installed successfully at: !TESSERACT_PATH!
    echo.
    echo Setting environment variable...
    setx TESSERACT_PATH "!TESSERACT_PATH!" >nul 2>&1
    echo [OK] Environment variable set (restart terminal to apply)
    echo.
    echo Tesseract installation complete!
    echo.
) else (
    echo.
    echo [WARNING] Tesseract installation may have failed
    echo.
    echo Manual installation options:
    echo   1. Run this script as Administrator and try again
    echo   2. Install via winget: winget install -e --id UB-Mannheim.TesseractOCR
    echo   3. Download from: https://github.com/tesseract-ocr/tesseract/wiki
    echo.
    echo The bot will still work, but scanned PDF processing may be limited.
    echo.
)

if not "%1"=="NO_PAUSE" (
    pause
)

:end
endlocal

