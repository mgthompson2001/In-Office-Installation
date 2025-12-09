@echo off
echo ================================================
echo ChromeDriver Quick Install
echo ================================================
echo.
echo This will help you install ChromeDriver manually
echo if the bot keeps failing with network errors.
echo.
pause

echo Checking Chrome version...
for /f "tokens=2 delims= " %%i in ('reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version 2^>nul') do set CHROME_VERSION=%%i
if "%CHROME_VERSION%"=="" (
    echo Chrome not found in registry. Please check your Chrome version manually.
    echo Go to Chrome menu ^> Help ^> About Google Chrome
    pause
    exit /b
)

echo Found Chrome version: %CHROME_VERSION%

echo.
echo Creating ChromeDriver directory...
if not exist "C:\chromedriver" mkdir "C:\chromedriver"

echo.
echo Downloading ChromeDriver...
echo This may take a moment...

powershell -Command "try { $version = '%CHROME_VERSION%'; $url = 'https://chromedriver.storage.googleapis.com/' + $version + '/chromedriver_win32.zip'; $output = 'C:\chromedriver\chromedriver.zip'; Invoke-WebRequest -Uri $url -OutFile $output; Write-Host 'Download successful!' } catch { Write-Host 'Download failed. Please check your internet connection.' }"

echo.
echo Extracting ChromeDriver...
powershell -Command "try { Expand-Archive -Path 'C:\chromedriver\chromedriver.zip' -DestinationPath 'C:\chromedriver' -Force; Write-Host 'Extraction successful!' } catch { Write-Host 'Extraction failed.' }"

echo.
echo Cleaning up...
del "C:\chromedriver\chromedriver.zip" 2>nul

echo.
echo ChromeDriver installation complete!
echo Location: C:\chromedriver\chromedriver.exe
echo.
echo You can now try running the bot again.
pause
