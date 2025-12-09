@echo off
echo ========================================
echo   Ghost Icon Troubleshooter
echo ========================================
echo.

REM Check icon file
echo Checking icon file...
if exist "%~dp0ccmd_bot_icon.ico" (
    echo [OK] Icon file exists
    for %%A in ("%~dp0ccmd_bot_icon.ico") do echo [INFO] Icon file size: %%~zA bytes
    echo [INFO] Expected size: around 2035 bytes
) else (
    echo [ERROR] Icon file NOT found!
    echo [ERROR] The icon file is missing from _system folder
    pause
    exit /b 1
)

echo.
echo Clearing Windows icon cache...
echo.

REM Delete old shortcut
if exist "%USERPROFILE%\Desktop\Automation Hub.lnk" (
    echo Deleting old shortcut...
    del /F "%USERPROFILE%\Desktop\Automation Hub.lnk"
    echo [OK] Old shortcut deleted
)

REM Clear icon cache
echo Clearing icon cache files...
del /F /Q "%LOCALAPPDATA%\IconCache.db" 2>nul
del /F /Q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db" 2>nul
echo [OK] Icon cache cleared

REM Restart Explorer
echo Restarting Windows Explorer...
taskkill /F /IM explorer.exe
timeout /T 2 /NOBREAK >nul
start explorer.exe
timeout /T 3 /NOBREAK >nul

echo.
echo ========================================
echo   Creating New Shortcut
echo ========================================
echo.

REM Run the installer
cd /d "%~dp0.."
python "_system\install_bots.py"

echo.
echo ========================================
echo   Troubleshooting Complete!
echo ========================================
echo.
echo Check your desktop for the new icon.
echo It should show a red pillar with vertical grooves.
echo.
echo If you still see a ghost icon:
echo   1. Take a screenshot
echo   2. Send it to IT
echo   3. Note your Windows version
echo.
pause

