@echo off
title Document Translator - Get Shareable Link
color 0B
echo.
echo ========================================
echo   Document Translator - Shareable Link
echo ========================================
echo.

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP:~1%

echo.
echo ========================================
echo   COPY AND SEND THIS LINK:
echo ========================================
echo.
echo   http://%IP%:5000
echo.
echo ========================================
echo.
echo Instructions:
echo   1. Copy the link above
echo   2. Send it to the person you want to share with
echo   3. Make sure they are on the same WiFi/network as you
echo   4. Run "start_web_server.bat" to start the server
echo   5. They can then use the link to access the translator
echo.
echo ========================================
echo.
pause

