@echo off
echo ========================================
echo CCMD Bot Centralized Management Setup
echo ========================================
echo.

echo This script will help you set up centralized computer management.
echo All computers will register in a shared location so you can see them all from one place.
echo.

echo Step 1: Choose a location for the shared folder
echo.
echo Option A - Network Server (Recommended for multiple computers):
echo   Create folder: \\YOUR_SERVER\CCMD_Bot_Manager
echo   Give all users read/write access
echo.
echo Option B - Local Shared Folder (For single machine or testing):
echo   Create folder: C:\CCMD_Bot_Manager
echo   Share it with full access
echo.
echo Option C - Use existing network share:
echo   Point to your existing shared folder
echo.

set /p choice="Choose option (A/B/C): "

if /i "%choice%"=="A" (
    echo.
    echo For Option A, you need to:
    echo 1. Create a folder on your server: \\YOUR_SERVER\CCMD_Bot_Manager
    echo 2. Share it with full read/write access for all users
    echo 3. Test access from each computer
    echo.
    echo The update manager will automatically detect this location.
    echo.
    pause
) else if /i "%choice%"=="B" (
    echo.
    echo Creating local shared folder...
    mkdir "C:\CCMD_Bot_Manager" 2>nul
    echo Folder created: C:\CCMD_Bot_Manager
    echo.
    echo To share this folder:
    echo 1. Right-click C:\CCMD_Bot_Manager
    echo 2. Properties ^> Sharing ^> Advanced Sharing
    echo 3. Check "Share this folder"
    echo 4. Permissions ^> Add "Everyone" with Full Control
    echo.
    pause
) else if /i "%choice%"=="C" (
    echo.
    set /p custom_path="Enter the full path to your shared folder: "
    echo.
    echo Testing access to: %custom_path%
    if exist "%custom_path%" (
        echo ✅ Folder exists and is accessible
        echo.
        echo The update manager will try to use this location automatically.
        echo Make sure all computers can read/write to this folder.
    ) else (
        echo ❌ Folder not found or not accessible
        echo Please check the path and try again.
    )
    echo.
    pause
) else (
    echo Invalid choice. Please run the script again.
    pause
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Restart the update manager on all computers
echo 2. All computers should now appear in the centralized list
echo 3. You can manage updates from any computer
echo.
echo If computers still don't appear:
echo - Check network connectivity
echo - Verify folder permissions
echo - Restart the update manager
echo.
pause
