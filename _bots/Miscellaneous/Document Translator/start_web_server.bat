@echo off
title Document Translator Web Server
color 0A
echo.
echo ========================================
echo   Document Translator Web Server
echo ========================================
echo.

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP:~1%

echo Your computer's IP address: %IP%
echo.
echo ========================================
echo   SHARE THIS LINK WITH OTHERS:
echo ========================================
echo.
echo   http://%IP%:5000
echo.
echo ========================================
echo.
echo Starting web server...
echo.
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo.

cd /d "%~dp0"
python web_translator_app.py

pause

