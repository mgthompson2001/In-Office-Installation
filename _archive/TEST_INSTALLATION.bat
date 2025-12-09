@echo off
REM ========================================
REM INSTALLATION TEST SCRIPT
REM Tests that all dependencies will install correctly
REM ========================================

echo ========================================
echo INSTALLATION TEST - Dependency Verification
echo ========================================
echo.
echo This script will verify that all dependencies
echo are properly configured for installation.
echo.
echo ========================================
echo.

REM Change to installation directory
cd /d "%~dp0"

REM Test 1: Check Python
echo [TEST 1] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Python is not installed or not in PATH
    echo   [FIX]  Install Python 3.8+ and add to PATH
    set TEST_FAILED=1
) else (
    python --version
    echo   [PASS] Python is available
)
echo.

REM Test 2: Check if _system directory exists
echo [TEST 2] Checking installation structure...
if not exist "_system" (
    echo   [FAIL] _system directory not found
    set TEST_FAILED=1
) else (
    echo   [PASS] _system directory exists
)
if not exist "_bots" (
    echo   [FAIL] _bots directory not found
    set TEST_FAILED=1
) else (
    echo   [PASS] _bots directory exists
)
echo.

REM Test 3: Check if install_for_employee.py exists
echo [TEST 3] Checking installation script...
if not exist "_system\install_for_employee.py" (
    echo   [FAIL] install_for_employee.py not found
    set TEST_FAILED=1
) else (
    echo   [PASS] install_for_employee.py exists
)
echo.

REM Test 4: Check if requirements.txt files exist
echo [TEST 4] Checking requirements files...
if not exist "_system\requirements.txt" (
    echo   [WARN] _system\requirements.txt not found
) else (
    echo   [PASS] _system\requirements.txt exists
)

if not exist "_bots\Billing Department\Medisoft Billing\requirements.txt" (
    echo   [WARN] Medisoft Billing requirements.txt not found
) else (
    echo   [PASS] Medisoft Billing requirements.txt exists
)

if not exist "_bots\Billing Department\TN Refiling Bot\requirements.txt" (
    echo   [WARN] TN Refiling Bot requirements.txt not found
) else (
    echo   [PASS] TN Refiling Bot requirements.txt exists
)
echo.

REM Test 5: Verify critical dependencies are in requirements
echo [TEST 5] Verifying critical dependencies are listed...
python -c "import re; req = open('_system/requirements.txt', 'r').read(); deps = ['PyPDF2', 'reportlab', 'fpdf2', 'pdfplumber', 'selenium', 'webdriver-manager']; missing = [d for d in deps if not re.search(r'^%s>=' % d, req, re.M)]; print('  [PASS] All critical dependencies found' if not missing else f'  [FAIL] Missing: {missing}')" 2>nul
if errorlevel 1 (
    echo   [WARN] Could not verify dependencies in requirements.txt
)
echo.

REM Test 6: Check if OCR setup script exists
echo [TEST 6] Checking OCR setup script...
if not exist "_bots\Billing Department\Medisoft Billing\setup\install_ocr.ps1" (
    echo   [WARN] OCR setup script not found (optional)
) else (
    echo   [PASS] OCR setup script exists
)
echo.

REM Test 7: Test Python script syntax
echo [TEST 7] Testing Python installation script syntax...
python -m py_compile "_system\install_for_employee.py" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] install_for_employee.py has syntax errors
    set TEST_FAILED=1
) else (
    echo   [PASS] install_for_employee.py syntax is valid
)
echo.

REM Test 8: Verify critical packages can be checked
echo [TEST 8] Testing package import verification...
python -c "packages = ['PyPDF2', 'reportlab', 'selenium', 'pandas', 'pdfplumber']; missing = [p for p in packages if __import__('pkgutil').find_loader(p) is None]; print(f'  [INFO] Currently installed: {[p for p in packages if p not in missing]}'); print(f'  [INFO] Will be installed: {missing}')" 2>nul
if errorlevel 1 (
    echo   [WARN] Could not check package status
)
echo.

REM Test 9: Check path references in install script
echo [TEST 9] Verifying path references...
python -c "from pathlib import Path; script = Path('_system/install_for_employee.py'); content = script.read_text(); checks = [('_system', '_system directory'), ('_bots', '_bots directory'), ('requirements.txt', 'requirements files')]; results = [(name, 'found' if name in content else 'missing') for name, desc in checks]; [print(f'  [PASS] {desc}: {name}') if status == 'found' else print(f'  [WARN] {desc}: {name} {status}') for name, status in results]" 2>nul
if errorlevel 1 (
    echo   [WARN] Could not verify path references
)
echo.

REM Test 10: Check if pip is available
echo [TEST 10] Checking pip availability...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] pip is not available
    set TEST_FAILED=1
) else (
    python -m pip --version
    echo   [PASS] pip is available
)
echo.

echo ========================================
echo TEST SUMMARY
echo ========================================
echo.

if defined TEST_FAILED (
    echo [RESULT] Some tests FAILED
    echo.
    echo Please fix the issues above before running installation.
    echo.
) else (
    echo [RESULT] All critical tests PASSED
    echo.
    echo The installation script should work correctly.
    echo You can proceed with running INSTALL_BOTS.bat
    echo.
)

echo ========================================
echo.
echo Note: This test does not actually install packages.
echo It only verifies that the installation setup is correct.
echo.
pause

