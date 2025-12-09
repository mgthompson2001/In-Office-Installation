@echo off
echo ========================================
echo CCMD Bot - Company Shared Drive Setup
echo ========================================
echo.

echo This will help you set up the CCMD Bot Manager on your company shared drive.
echo All computers will register in this shared location.
echo.

echo Step 1: Find your company shared drive
echo.
echo Common shared drive locations:
echo - \\\\server\\shared
echo - \\\\fileserver\\company
echo - \\\\network\\shared
echo - \\\\company\\files
echo.

set /p shared_drive="Enter your company shared drive path (e.g., \\\\server\\shared): "

echo.
echo Step 2: Create the CCMD_Bot_Manager folder
echo.

echo Creating folder: %shared_drive%\CCMD_Bot_Manager
mkdir "%shared_drive%\CCMD_Bot_Manager" 2>nul

if exist "%shared_drive%\CCMD_Bot_Manager" (
    echo ✅ Folder created successfully
    echo.
    echo Step 3: Set permissions
    echo.
    echo The folder has been created. You may need to:
    echo 1. Right-click the folder in Windows Explorer
    echo 2. Properties ^> Security ^> Edit
    echo 3. Add "Everyone" or "Domain Users" with Full Control
    echo 4. Or ask your IT department to set the permissions
    echo.
    echo Step 4: Test access
    echo.
    echo Testing write access...
    echo test > "%shared_drive%\CCMD_Bot_Manager\test.txt" 2>nul
    if exist "%shared_drive%\CCMD_Bot_Manager\test.txt" (
        del "%shared_drive%\CCMD_Bot_Manager\test.txt" 2>nul
        echo ✅ Write access confirmed
        echo.
        echo ========================================
        echo Setup Complete!
        echo ========================================
        echo.
        echo The shared folder is ready at:
        echo %shared_drive%\CCMD_Bot_Manager
        echo.
        echo Next steps:
        echo 1. Restart the update manager on ALL computers
        echo 2. All computers should now appear in the centralized list
        echo 3. You can manage updates from any computer
        echo.
        echo If computers don't appear:
        echo - Check that all computers can access the shared drive
        echo - Verify permissions are set correctly
        echo - Restart the update manager on all computers
    ) else (
        echo ❌ Write access denied
        echo.
        echo You need to set permissions on the folder:
        echo 1. Right-click %shared_drive%\CCMD_Bot_Manager
        echo 2. Properties ^> Security ^> Edit
        echo 3. Add "Everyone" with Full Control
        echo 4. Or contact your IT department
    )
) else (
    echo ❌ Failed to create folder
    echo.
    echo Possible issues:
    echo - You don't have permission to create folders on the shared drive
    echo - The shared drive path is incorrect
    echo - The shared drive is not accessible
    echo.
    echo Please check the path and try again, or contact your IT department.
)

echo.
pause
