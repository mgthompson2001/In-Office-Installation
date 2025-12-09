@echo off
echo ========================================
echo Document Translator Web Server
echo ========================================
echo.
echo Starting web server...
echo Access the application at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

cd /d "%~dp0"
python web_translator_app.py

pause

