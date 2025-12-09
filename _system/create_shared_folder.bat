@echo off
echo ========================================
echo CCMD Bot Shared Folder Setup
echo ========================================
echo.

echo This will create a shared folder that all computers can use.
echo All computers will register in this shared location.
echo.

echo Step 1: Choose where to create the shared folder
echo.
echo Option 1 - Local C: Drive (Recommended for testing):
echo   Creates: C:\CCMD_Bot_Manager
echo   Shares it with full access
echo.
echo Option 2 - Local D: Drive (If you have a D: drive):
echo   Creates: D:\CCMD_Bot_Manager  
echo   Shares it with full access
echo.
echo Option 3 - Network Server (Advanced):
echo   You'll need to create this manually on your server
echo.

set /p choice="Choose option (1/2/3): "

if "%choice%"=="1" (
    echo.
    echo Creating C:\CCMD_Bot_Manager...
    mkdir "C:\CCMD_Bot_Manager" 2>nul
    if exist "C:\CCMD_Bot_Manager" (
        echo ✅ Folder created successfully
        echo.
        echo Now sharing the folder...
        net share CCMD_Bot_Manager=C:\CCMD_Bot_Manager /GRANT:Everyone,FULL 2>nul
        echo ✅ Folder shared successfully
        echo.
        echo The shared folder is now available at:
        echo \\%COMPUTERNAME%\CCMD_Bot_Manager
        echo.
        echo Next steps:
        echo 1. Restart the update manager on this computer
        echo 2. Restart the update manager on all other computers
        echo 3. All computers should now appear in the centralized list
    ) else (
        echo ❌ Failed to create folder. You may need administrator privileges.
        echo Please run this script as administrator.
    )
) else if "%choice%"=="2" (
    echo.
    echo Creating D:\CCMD_Bot_Manager...
    mkdir "D:\CCMD_Bot_Manager" 2>nul
    if exist "D:\CCMD_Bot_Manager" (
        echo ✅ Folder created successfully
        echo.
        echo Now sharing the folder...
        net share CCMD_Bot_Manager=D:\CCMD_Bot_Manager /GRANT:Everyone,FULL 2>nul
        echo ✅ Folder shared successfully
        echo.
        echo The shared folder is now available at:
        echo \\%COMPUTERNAME%\CCMD_Bot_Manager
        echo.
        echo Next steps:
        echo 1. Restart the update manager on this computer
        echo 2. Restart the update manager on all other computers
        echo 3. All computers should now appear in the centralized list
    ) else (
        echo ❌ Failed to create folder. D: drive may not exist or you need administrator privileges.
        echo Please run this script as administrator.
    )
) else if "%choice%"=="3" (
    echo.
    echo For network server setup:
    echo.
    echo 1. Create a folder on your server: \\YOUR_SERVER\CCMD_Bot_Manager
    echo 2. Share it with full read/write access for all users
    echo 3. Test access from each computer
    echo 4. Restart the update manager on all computers
    echo.
    echo The update manager will automatically detect this location.
) else (
    echo Invalid choice. Please run the script again.
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Important: You must restart the update manager on ALL computers
echo for them to start using the shared location.
echo.
pause
