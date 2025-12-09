@echo off
REM Test script to verify installer logic without actually installing
REM This checks all the components that will be used during installation

echo ================================================
echo Installer Test - Component Verification
echo ================================================
echo.

REM Check if we're in the right location
if not exist "Installer\Install.bots" (
    echo [ERROR] Install.bots not found!
    echo Please run this from the root directory
    pause
    exit /b 1
)

echo [OK] Install.bots found
echo.

REM Check Python installer script
if exist "Installer\install_python.ps1" (
    echo [OK] install_python.ps1 found
) else (
    echo [ERROR] install_python.ps1 not found!
    pause
    exit /b 1
)

REM Check OCR installer script
if exist "Installer\install_ocr_dependencies.ps1" (
    echo [OK] install_ocr_dependencies.ps1 found
) else (
    echo [ERROR] install_ocr_dependencies.ps1 not found!
    pause
    exit /b 1
)

REM Check other required scripts
set "SCRIPTS=setup_icon.py configure_paths.py migrate_saved_data.py create_desktop_shortcut.vbs"
for %%s in (%SCRIPTS%) do (
    if exist "Installer\%%s" (
        echo [OK] %%s found
    ) else (
        echo [WARNING] %%s not found
    )
)

echo.
echo ================================================
echo Python Version Check Test
echo ================================================
echo.

REM Test Python version check
if exist "Installer\check_python_version.py" (
    python "Installer\check_python_version.py" 2>nul
    if errorlevel 1 (
        echo [INFO] Python version check indicates incompatible version
        echo        This is expected if Python 3.14+ is installed
    ) else (
        echo [OK] Python version check passed
    )
) else (
    echo [WARNING] check_python_version.py not found
)

echo.
echo ================================================
echo Path Verification Test
echo ================================================
echo.

REM Check if bot directory exists
if exist "_bots\Billing Department\Medisoft Billing\medisoft_billing_bot.py" (
    echo [OK] Bot directory found
) else (
    echo [ERROR] Bot directory not found!
    echo Expected: _bots\Billing Department\Medisoft Billing\medisoft_billing_bot.py
    pause
    exit /b 1
)

REM Check requirements.txt
if exist "_bots\Billing Department\Medisoft Billing\requirements.txt" (
    echo [OK] requirements.txt found
) else (
    echo [WARNING] requirements.txt not found
)

echo.
echo ================================================
echo PowerShell Execution Policy Test
echo ================================================
echo.

REM Test if PowerShell can run scripts
powershell -NoProfile -ExecutionPolicy Bypass -Command "Write-Host '[OK] PowerShell execution policy bypass works'" 2>nul
if errorlevel 1 (
    echo [WARNING] PowerShell execution policy may be restricted
    echo           Installer may need Administrator rights
) else (
    echo [OK] PowerShell can execute scripts
)

echo.
echo ================================================
echo Installation Readiness Check
echo ================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Python not found - installer will install Python 3.11 automatically
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
    echo [INFO] Python found: %PYTHON_VER%
    REM Check if version is compatible
    python "Installer\check_python_version.py" 2>nul
    if errorlevel 1 (
        echo [INFO] Python version incompatible - installer will install Python 3.11 automatically
    ) else (
        echo [OK] Python version is compatible
    )
)

echo.
echo ================================================
echo Test Complete
echo ================================================
echo.
echo Summary:
echo   - All required installer scripts are present
echo   - Installation logic should work correctly
echo   - Python will be installed automatically if needed
echo.
echo Ready for installation!
echo.
pause

