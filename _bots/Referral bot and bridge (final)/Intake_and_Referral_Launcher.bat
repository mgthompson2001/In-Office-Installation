@echo off
REM Intake and Referral Sub-Launcher
REM This launcher provides quick access to all intake and referral related bots

echo ========================================
echo Intake and Referral Bot Launcher
echo ========================================
echo.
echo Please select a bot to launch:
echo.
echo 1. IPS/IA Referral Form Uploader (Dual Tab)
echo 2. Existing Client Referral Form Uploader
echo 3. Counselor Assignment Bot
echo 4. Referral Document Cleanup Bot
echo 5. Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    echo.
    echo Launching IPS/IA Referral Form Uploader...
    start "" "IPS_IA_Referral_Form_Uploader_Dual_Tab.bat"
    goto :end
)

if "%choice%"=="2" (
    echo.
    echo Launching Existing Client Referral Form Uploader...
    start "" "existing_client_referral_form_uploader.py"
    goto :end
)

if "%choice%"=="3" (
    echo.
    echo Launching Counselor Assignment Bot...
    start "" "counselor_assignment_bot.bat"
    goto :end
)

if "%choice%"=="4" (
    echo.
    echo Launching Referral Document Cleanup Bot...
    REM Navigate to the Referral Document Cleanup Bot directory
    cd /d "%~dp0\..\Billing Department\Medisoft Billing\Referral Document Cleanup Bot"
    start "" "referral_document_cleanup_bot.bat"
    goto :end
)

if "%choice%"=="5" (
    echo.
    echo Exiting...
    goto :end
)

echo.
echo Invalid choice. Please try again.
pause

:end
exit /b 0

