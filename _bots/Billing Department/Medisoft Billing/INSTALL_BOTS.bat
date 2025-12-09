@echo off
setlocal enabledelayedexpansion

REM ==============================================
REM  CCMD Bot Installation - Main Installer
REM  FIXED: Automatically installs Python 3.11 if Python 3.14+ is found
REM ==============================================

echo.
echo ================================================
echo  CCMD Bot Installation - Main Installer
echo ================================================
echo.
echo This will install all required dependencies and create
echo the desktop shortcut for launching all bots.
echo.
echo IMPORTANT: This installer will automatically install Python 3.11
echo if Python 3.14 or incompatible version is detected.
echo.
pause

REM Change to the In-Office Installation directory (this script's directory)    
cd /d "%~dp0"

REM ==========================================
REM CRITICAL STEP 1: Python Detection & Installation
REM ==========================================
echo.
echo ================================================
echo  STEP 1: Python Installation Check (CRITICAL)
echo ================================================
echo.

set "PYTHON_CMD="
set "PYTHON_VERSION="
set "PYTHON_NEEDS_INSTALL=0"

REM Check if Python exists and get version
python --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Python not found - will install Python 3.11
    set "PYTHON_NEEDS_INSTALL=1"
) else (
    REM Get version string
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [INFO] Found Python: %PYTHON_VERSION%
    
    REM Check if version is 3.13+ (incompatible - causes NumPy compilation errors)
    echo %PYTHON_VERSION% | findstr /R "^3\.1[3-9] ^3\.[2-9]" >nul
    if not errorlevel 1 (
        echo [WARNING] Python %PYTHON_VERSION% is TOO NEW and INCOMPATIBLE
        echo          Packages don't have wheels for Python 3.14+
        echo          This causes NumPy compilation errors
        echo          Will install Python 3.11 now...
        set "PYTHON_NEEDS_INSTALL=1"
    ) else (
        REM Check if compatible (3.7-3.12)
        echo %PYTHON_VERSION% | findstr /R "^3\.[7-9] ^3\.1[0-2]" >nul
        if not errorlevel 1 (
            echo [OK] Python %PYTHON_VERSION% is compatible
            set "PYTHON_CMD=python"
            goto :python_ready
        ) else (
            REM Unknown version - try compatibility check script
            set "CHECK_SCRIPT=%~dp0Installer\check_python_version.py"
            if exist "%CHECK_SCRIPT%" (
                python "%CHECK_SCRIPT%" >nul 2>&1
                if errorlevel 1 (
                    echo [WARNING] Python %PYTHON_VERSION% may not be compatible
                    echo          Will install Python 3.11 to ensure compatibility...
                    set "PYTHON_NEEDS_INSTALL=1"
                ) else (
                    echo [OK] Python %PYTHON_VERSION% verified as compatible
                    set "PYTHON_CMD=python"
                    goto :python_ready
                )
            ) else (
                REM No check script - assume incompatible and install
                echo [WARNING] Cannot verify Python compatibility
                echo          Will install Python 3.11 to ensure compatibility...
                set "PYTHON_NEEDS_INSTALL=1"
            )
        )
    )
)

REM Install Python 3.11 if needed
if "%PYTHON_NEEDS_INSTALL%"=="1" (
    echo.
    echo ================================================
    echo  Installing Python 3.11.10
    echo ================================================
    echo.
    if defined PYTHON_VERSION (
        echo Current Python %PYTHON_VERSION% is incompatible.
        echo Installing Python 3.11.10 (compatible version)...
    ) else (
        echo Python not found.
        echo Installing Python 3.11.10...
    )
    echo.
    echo This may take a few minutes...
    echo.
    
    set "PYTHON_INSTALLER=%~dp0Installer\install_python.ps1"
    if exist "%PYTHON_INSTALLER%" (
        powershell -NoProfile -ExecutionPolicy Bypass -File "%PYTHON_INSTALLER%" -PreferredVersion "3.11.10"
        set PYTHON_INSTALL_EXIT=%ERRORLEVEL%
        
        if !PYTHON_INSTALL_EXIT! NEQ 0 (
            echo.
            echo [ERROR] Python installation failed (exit code: !PYTHON_INSTALL_EXIT!)
            echo Please install Python 3.10 or 3.11 manually from https://www.python.org/
            echo Make sure to check "Add Python to PATH" during installation
            pause
            exit /b 1
        )
        
        echo.
        echo [OK] Python installation complete
        echo.
        echo Refreshing environment... This may take a moment...
        
        REM Wait for installation to fully complete
        timeout /t 10 /nobreak >nul
        
        REM Refresh PATH from registry (comprehensive)
        for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYSTEM_PATH=%%b"
        for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"
        set "PATH=!SYSTEM_PATH!;!USER_PATH!"
        
        REM Use PowerShell to refresh PATH more reliably
        powershell -NoProfile -Command "$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')"
        
        timeout /t 5 /nobreak >nul
    ) else (
        echo [ERROR] Python installer not found at: %PYTHON_INSTALLER%
        echo Please install Python 3.10 or 3.11 manually from https://www.python.org/
        pause
        exit /b 1
    )
)

REM Find the correct Python command to use (try Python 3.11 locations first)
:python_ready
REM Try Python 3.11 locations first (most reliable after installation)
set "PYTHON_311_LOCATIONS=C:\Program Files\Python311\python.exe;C:\Program Files (x86)\Python311\python.exe;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe;C:\Python311\python.exe"

for %%p in (%PYTHON_311_LOCATIONS%) do (
    if exist "%%p" (
        "%%p" --version >nul 2>&1
        if not errorlevel 1 (
            for /f "tokens=2" %%i in ('"%%p" --version 2^>^&1') do set PYTHON_VERSION=%%i
            echo %%i | findstr /R "^3\.1[0-2]" >nul
            if not errorlevel 1 (
                set "PYTHON_CMD=%%p"
                echo [OK] Using Python: %%p (version: %%i)
                goto :python_found
            )
        )
    )
)

REM Try py launcher with version specifier (preferred method)
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    for /f "tokens=2" %%i in ('py -3.11 --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Using Python: py -3.11 (version: %PYTHON_VERSION%)
    goto :python_found
)

REM Try py -3.10
py -3.10 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.10"
    for /f "tokens=2" %%i in ('py -3.10 --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Using Python: py -3.10 (version: %PYTHON_VERSION%)
    goto :python_found
)

REM Last resort: try python command (but verify it's not 3.14)
if not defined PYTHON_CMD (
    python --version >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
        REM Verify it's NOT 3.13+
        echo %PYTHON_VERSION% | findstr /R "^3\.1[3-9] ^3\.[2-9]" >nul
        if errorlevel 1 (
            REM Version is OK (3.7-3.12)
            set "PYTHON_CMD=python"
            echo [OK] Using Python: python (version: %PYTHON_VERSION%)
            goto :python_found
        ) else (
            echo [ERROR] Python %PYTHON_VERSION% is still in PATH (incompatible)
            echo          Python 3.11 was installed but PATH not refreshed
            echo          Please close this window and restart terminal
            echo          Then run the installer again
            echo.
            echo          Or manually use: py -3.11
            pause
            exit /b 1
        )
    )
)

echo [ERROR] Could not find compatible Python after installation
echo Please restart your terminal and run the installer again
echo Or manually install Python 3.11 from https://www.python.org/
pause
exit /b 1

:python_found
echo.
echo ================================================
echo  Python Verification Complete
echo ================================================
echo.
echo [OK] Using Python: %PYTHON_CMD%
%PYTHON_CMD% --version
echo [INFO] All subsequent steps will use this Python version
echo.

REM ==========================================
REM Step 2: Upgrade pip
REM ==========================================
echo ================================================
echo  STEP 2: Upgrading pip
echo ================================================
echo.

%PYTHON_CMD% -m pip install --quiet --upgrade pip --no-warn-script-location
if errorlevel 1 (
    echo [WARNING] pip upgrade failed, continuing anyway...
)
echo.

REM ==========================================
REM Step 3: Main Installation Script
REM ==========================================
echo ================================================
echo  STEP 3: Running main installation script
echo ================================================
echo.
echo Using Python: %PYTHON_CMD%
echo This will install all dependencies and create the desktop shortcut.
echo.

REM Run the main installation script with the CORRECT Python
%PYTHON_CMD% "Installer\install_for_employee.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Main installation failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ================================================
echo  STEP 3 Complete
echo ================================================
echo.
echo [OK] Main installation completed successfully!
echo.

REM ==========================================
REM Step 4: Medisoft Billing Bot Installation
REM ==========================================
echo ================================================
echo  STEP 4: Medisoft Billing Bot Installation
echo ================================================
echo.
echo This will install all dependencies, OCR tools, desktop shortcut, and migrate saved data.
echo Using Python: %PYTHON_CMD%
echo.

set "MEDISOFT_INSTALLER=%~dp0Installer\Install.bots"

if exist %MEDISOFT_INSTALLER% (
    echo Running Medisoft Billing Bot installer...
    echo.
    echo This installer handles:
    echo   - Python dependencies (flexible detection - works with existing installs)
    echo   - OCR dependencies (Tesseract, Poppler) - automatic installation
    echo   - Desktop shortcut with red I icon (fixes blank icon issue)
    echo   - Saved selectors migration (preserves employee configurations)
    echo   - Path configuration (works from any installation location)
    echo.
    
    REM Pass Python command to Medisoft installer via environment variable
    set "REQUIRED_PYTHON_CMD=%PYTHON_CMD%"
    call %MEDISOFT_INSTALLER%
    set MEDISOFT_EXIT=%ERRORLEVEL%
    
    if !MEDISOFT_EXIT! NEQ 0 (
        echo.
        echo [WARNING] Medisoft Billing Bot installation encountered some issues.
        echo The bot may still work, but some features may be limited.
        echo You can run the installer manually later: Installer\Install.bots
        echo.
    ) else (
        echo.
        echo [OK] Medisoft Billing Bot installation completed successfully!
        echo.
    )
) else (
    echo [SKIP] Medisoft Billing Bot installer not found at: %MEDISOFT_INSTALLER%
    echo You can run it manually: Installer\Install.bots
    echo Or use the legacy installer: _bots\Billing Department\Medisoft Billing\install.bat
    echo.
)

echo.
echo ================================================
echo Installation Summary
echo ================================================
echo.
echo Installation complete! Check the following:
echo.
echo 1. Desktop shortcut "Automation Hub" should be on your desktop
echo 2. Desktop shortcut "Medisoft Billing Bot" should be on your desktop
echo 3. Both shortcuts should have a RED "I" icon (not blank)
echo 4. Double-click the shortcuts to launch the bots
echo.
echo Python used for installation: %PYTHON_CMD%
echo Python version: %PYTHON_VERSION%
echo.
echo If you don't see the desktop shortcuts:
echo   - Check if you have permission to create desktop shortcuts
echo   - Try running this installer as Administrator
echo   - Contact IT support
echo.
echo If the icon is blank (white page):
echo   - The icon file may not be accessible
echo   - Try running this installer as Administrator
echo   - Restart your computer (refreshes icon cache)
echo   - Contact IT support
echo.
echo If you see errors about missing modules:
echo   - The installer should have installed them automatically
echo   - This includes PDF creation libraries (PyPDF2, reportlab, fpdf2)        
echo   - This includes web automation (selenium, webdriver-manager, playwright) 
echo   - This includes modern data processing (polars, loguru, pydantic)        
echo   - If not, contact IT support with the error message
echo.
echo ================================================
pause

:end
endlocal
