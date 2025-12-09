@echo off
echo ========================================
echo    CCMD Bot Custom Logo Creator
echo ========================================
echo.

REM Check if an image file was provided
if "%~1"=="" (
    echo Please provide the path to your logo image file.
    echo.
    echo Usage: create_custom_logo.bat "path\to\your\logo.png"
    echo.
    echo Example: create_custom_logo.bat "C:\Users\YourName\Desktop\my_logo.png"
    echo.
    pause
    exit /b 1
)

REM Check if the file exists
if not exist "%~1" (
    echo Error: The file "%~1" does not exist.
    echo Please check the path and try again.
    echo.
    pause
    exit /b 1
)

echo Creating icons from your custom logo...
echo Source image: %~1
echo.

REM Run the Python script with the custom image
python create_icon.py "%~1"

echo.
echo ========================================
echo    Logo creation complete!
echo ========================================
echo.
echo Your custom logo has been converted to:
echo - ccmd_bot_icon.ico (for Windows shortcuts)
echo - cmd_bot_icon.png (for general use)
echo.
echo The installer will use these files automatically.
echo.
pause
