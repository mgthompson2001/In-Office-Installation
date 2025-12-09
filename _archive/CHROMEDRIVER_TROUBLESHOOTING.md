# ChromeDriver Installation Guide

## If the Counselor Assignment Bot Still Fails

If you're getting "Could not reach host. Are you offline?" errors, follow these steps:

### Method 1: Manual ChromeDriver Installation (Recommended)

1. **Check your Chrome version:**
   - Open Chrome browser
   - Click the 3 dots menu → Help → About Google Chrome
   - Note the version number (e.g., "Version 131.0.6778.108")

2. **Download ChromeDriver:**
   - Go to: https://chromedriver.chromium.org/downloads
   - Find the version that matches your Chrome version
   - Download `chromedriver_win32.zip`

3. **Install ChromeDriver:**
   - Extract the zip file
   - Copy `chromedriver.exe` to one of these locations:
     - `C:\chromedriver\chromedriver.exe` (create the folder)
     - `C:\Windows\System32\chromedriver.exe` (requires admin rights)

4. **Test the bot again**

### Method 2: Use System ChromeDriver

If ChromeDriver is already installed on your system:
1. Open Command Prompt
2. Type: `chromedriver --version`
3. If it shows a version, the bot should work
4. If not, use Method 1 above

### Method 3: Network Troubleshooting

If the download keeps failing:
1. **Check your internet connection**
2. **Try a different network** (mobile hotspot, different WiFi)
3. **Disable VPN** if you're using one
4. **Check corporate firewall** - ask IT to allow `googlechromelabs.github.io`

### Method 4: Offline Installation

If you can't download ChromeDriver:
1. Ask a colleague who has the bot working to share their `chromedriver.exe`
2. Place it in `C:\chromedriver\chromedriver.exe`
3. Make sure the version matches your Chrome browser

## Still Having Issues?

Contact IT support with:
- Your Chrome version number
- The exact error message
- Which method you tried
- Your network environment (corporate, home, etc.)

## Quick Fix Commands

Run these in Command Prompt as Administrator:
```cmd
# Create ChromeDriver directory
mkdir C:\chromedriver

# Download ChromeDriver (replace VERSION with your Chrome version)
# Example: powershell -Command "Invoke-WebRequest -Uri 'https://chromedriver.storage.googleapis.com/131.0.6778.108/chromedriver_win32.zip' -OutFile 'C:\chromedriver\chromedriver.zip'"

# Extract and test
# (You'll need to manually extract the zip file)
```
