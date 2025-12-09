@echo off
echo ========================================
echo   Icon Diagnostic Tool
echo ========================================
echo.
echo Collecting information...
echo.

REM Get current location
echo FOLDER LOCATION:
echo %~dp0
echo.

REM Check icon file
echo ICON FILE CHECK:
if exist "%~dp0ccmd_bot_icon.ico" (
    echo [OK] Icon file exists
    for %%A in ("%~dp0ccmd_bot_icon.ico") do (
        echo     Size: %%~zA bytes
        echo     Path: %%~fA
    )
) else (
    echo [ERROR] Icon file NOT found!
)
echo.

REM Check shortcut
echo DESKTOP SHORTCUT CHECK:
if exist "%USERPROFILE%\Desktop\Automation Hub.lnk" (
    echo [OK] Shortcut exists
    echo     Location: %USERPROFILE%\Desktop\Automation Hub.lnk
) else (
    echo [WARNING] Shortcut not found on desktop
)
echo.

REM Save to file
echo ========================================
echo.
echo This information has been saved to: diagnostic_info.txt
echo Please send this file to IT support.
echo.

(
    echo DIAGNOSTIC REPORT
    echo Generated: %date% %time%
    echo.
    echo Installation Folder:
    echo %~dp0
    echo.
    echo Icon File:
    if exist "%~dp0ccmd_bot_icon.ico" (
        for %%A in ("%~dp0ccmd_bot_icon.ico") do (
            echo     Exists: YES
            echo     Size: %%~zA bytes
            echo     Full path: %%~fA
        )
    ) else (
        echo     Exists: NO
    )
    echo.
    echo Desktop Shortcut:
    if exist "%USERPROFILE%\Desktop\Automation Hub.lnk" (
        echo     Exists: YES
    ) else (
        echo     Exists: NO
    )
    echo.
    echo User Profile:
    echo %USERPROFILE%
    echo.
    echo Downloads Folder:
    echo %USERPROFILE%\Downloads
) > "%~dp0diagnostic_info.txt"

echo.
pause

