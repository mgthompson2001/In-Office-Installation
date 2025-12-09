@echo off
REM ========================================
REM BOT CONFIGURATION VERIFICATION SCRIPT
REM ========================================
REM This script verifies that all bot configuration files are present
REM Run this after transferring bots to a new computer
REM ========================================

echo ========================================
echo BOT CONFIGURATION VERIFICATION
echo ========================================
echo.
echo Checking for bot configuration files...
echo.

set "SCRIPT_DIR=%~dp0"
set "MISSING_FILES=0"

REM Function to check if file exists
:check_file
if exist "%~1" (
    echo   [OK] %~1
) else (
    echo   [MISSING] %~1
    set /a MISSING_FILES+=1
)
goto :eof

echo [Medisoft Billing Bot]
call :check_file "%SCRIPT_DIR%Billing Department\Medisoft Billing\medisoft_users.json"
call :check_file "%SCRIPT_DIR%Billing Department\Medisoft Billing\medisoft_coordinates.json"
echo.

echo [Penelope Workflow Tool]
call :check_file "%SCRIPT_DIR%Penelope Workflow Tool\penelope_users.json"
echo.

echo [Welcome Letter Bot]
call :check_file "%SCRIPT_DIR%The Welcomed One, Exalted Rank\welcome_bot_users.json"
call :check_file "%USERPROFILE%\Documents\ISWS Welcome\learned_pn_selectors.json"
echo.

echo [TN Refiling Bot]
call :check_file "%SCRIPT_DIR%Billing Department\TN Refiling Bot\tn_users.json"
call :check_file "%SCRIPT_DIR%Billing Department\TN Refiling Bot\tn_coordinates.json"
echo.

echo [Medicare Refiling Bot]
call :check_file "%SCRIPT_DIR%Billing Department\Medicare Refiling Bot\medicare_users.json"
call :check_file "%SCRIPT_DIR%Billing Department\Medicare Refiling Bot\pdf_field_mapping_config.json"
echo.

echo [Medical Records Bot]
call :check_file "%SCRIPT_DIR%Med Rec\therapy_notes_records_users.json"
call :check_file "%SCRIPT_DIR%Med Rec\therapy_notes_records_settings.json"
echo.

echo ========================================
if %MISSING_FILES% EQU 0 (
    echo All configuration files found!
    echo.
    echo Your bots are properly configured with saved:
    echo   - User credentials
    echo   - Coordinate training data
    echo   - Selector configurations
    echo   - Bot memory and settings
) else (
    echo WARNING: %MISSING_FILES% configuration file(s) missing!
    echo.
    echo Missing files will be created automatically when you:
    echo   1. Run the bot for the first time
    echo   2. Add a user or train the bot
    echo.
    echo However, any previously saved data (users, coordinates, selectors)
    echo will need to be re-entered or re-trained.
    echo.
    echo If you're transferring from another computer, make sure to copy:
    echo   - All *.json files from each bot folder
    echo   - All *.png image files (screenshots for recognition)
    echo   - learned_pn_selectors.json from Documents\ISWS Welcome\
)
echo ========================================
echo.
pause

