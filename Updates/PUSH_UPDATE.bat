@echo off
REM Simple script to push updates - just double-click this!
REM This runs both release_update.py and sync_to_gdrive.py

echo ========================================
echo Push Update to All Employees
echo ========================================
echo.

cd /d "%~dp0\.."

echo Step 1: Update version number...
echo.
set /p VERSION="Enter new version number (e.g., 1.0.1): "
set /p NOTES="Enter what changed (e.g., Fixed login bug): "

echo.
echo Updating version to %VERSION%...
python Updates\release_update.py %VERSION% "%NOTES%"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to update version
    pause
    exit /b 1
)

echo.
echo ========================================
echo Step 2: Pushing to G-Drive...
echo ========================================
echo.

python Updates\sync_to_gdrive.py %VERSION%

if errorlevel 1 (
    echo.
    echo ERROR: Failed to sync to G-Drive
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! Updates pushed to G-Drive!
echo ========================================
echo.
echo Employees will see updates when they start their bots.
echo.
pause
