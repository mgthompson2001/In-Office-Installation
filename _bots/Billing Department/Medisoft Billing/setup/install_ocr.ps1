# Requires: Windows PowerShell 5+ or PowerShell 7+
# Purpose: Install/configure Tesseract OCR and Poppler for this bot

$ErrorActionPreference = 'Continue'  # Changed from 'Stop' to allow fallbacks

Write-Host "=== Medisoft Bot - OCR Dependency Installer ===" -ForegroundColor Cyan
Write-Host ""

# Determine script and project directories
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$VendorDir = Join-Path $ProjectDir 'vendor'
New-Item -ItemType Directory -Force -Path $VendorDir | Out-Null

# Helper: Test command exists
function Test-Command($name) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  return $null -ne $cmd
}

# Helper: Check if running as admin
function Test-Administrator {
  $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# 1) Install Tesseract
Write-Host "Checking for Tesseract OCR..." -ForegroundColor Cyan
$TesseractExe = @(
  "$Env:ProgramFiles\Tesseract-OCR\tesseract.exe",
  "$Env:ProgramFiles(x86)\Tesseract-OCR\tesseract.exe",
  "$Env:LocalAppData\Programs\Tesseract-OCR\tesseract.exe",
  (Join-Path $VendorDir 'Tesseract-OCR\tesseract.exe')
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $TesseractExe) {
  Write-Host "Tesseract not found. Attempting installation..." -ForegroundColor Yellow
  
  # Method 1: Try winget (requires admin for system install)
  if (Test-Command 'winget') {
    Write-Host "  Trying winget installation..." -ForegroundColor Yellow
    try {
      $wingetResult = winget install -e --id UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements 2>&1
      if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Tesseract installed via winget" -ForegroundColor Green
        Start-Sleep -Seconds 2  # Give installer time to complete
      }
    } catch {
      Write-Host "  ✗ winget installation failed (may need admin rights)" -ForegroundColor Yellow
    }
    
    # Check again after winget attempt
    $TesseractExe = @(
      "$Env:ProgramFiles\Tesseract-OCR\tesseract.exe",
      "$Env:ProgramFiles(x86)\Tesseract-OCR\tesseract.exe",
      "$Env:LocalAppData\Programs\Tesseract-OCR\tesseract.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
  }
  
  # Method 2: Download portable Tesseract (fallback)
  if (-not $TesseractExe) {
    Write-Host "  Trying portable download..." -ForegroundColor Yellow
    try {
      $TesseractUrl = 'https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe'
      $TesseractInstaller = Join-Path $env:TEMP 'tesseract-installer.exe'
      
      Write-Host "  Downloading Tesseract installer..." -ForegroundColor Yellow
      Invoke-WebRequest -Uri $TesseractUrl -OutFile $TesseractInstaller -UseBasicParsing -ErrorAction Stop
      
      Write-Host "  Running installer (silent mode)..." -ForegroundColor Yellow
      $installArgs = "/S /D=$VendorDir\Tesseract-OCR"
      Start-Process -FilePath $TesseractInstaller -ArgumentList $installArgs -Wait -NoNewWindow
      
      # Check if installed
      $TesseractExe = Join-Path $VendorDir 'Tesseract-OCR\tesseract.exe'
      if (Test-Path $TesseractExe) {
        Write-Host "  ✓ Tesseract installed to vendor directory" -ForegroundColor Green
      } else {
        # Try default install location
        $TesseractExe = @(
          "$Env:ProgramFiles\Tesseract-OCR\tesseract.exe",
          "$Env:ProgramFiles(x86)\Tesseract-OCR\tesseract.exe"
        ) | Where-Object { Test-Path $_ } | Select-Object -First 1
      }
      
      # Clean up installer
      if (Test-Path $TesseractInstaller) {
        Remove-Item $TesseractInstaller -Force -ErrorAction SilentlyContinue
      }
    } catch {
      Write-Host "  ✗ Portable download failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
  }
}

if ($TesseractExe) {
  Write-Host "✓ Tesseract found at: $TesseractExe" -ForegroundColor Green
  [Environment]::SetEnvironmentVariable('TESSERACT_PATH', $TesseractExe, 'User')
  Write-Host "  Environment variable TESSERACT_PATH set (restart terminal to apply)" -ForegroundColor Gray
} else {
  Write-Host "✗ Could not auto-install Tesseract." -ForegroundColor Red
  Write-Host "  Manual installation options:" -ForegroundColor Yellow
  Write-Host "    1. Run as Administrator and try again" -ForegroundColor Yellow
  Write-Host "    2. Install manually: winget install -e --id UB-Mannheim.TesseractOCR" -ForegroundColor Yellow
  Write-Host "    3. Download from: https://github.com/tesseract-ocr/tesseract/wiki" -ForegroundColor Yellow
}
Write-Host ""

# 2) Install Poppler
Write-Host "Checking for Poppler..." -ForegroundColor Cyan
$PopplerBin = @(
  "$Env:ProgramFiles\poppler\Library\bin",
  "$Env:ProgramFiles(x86)\poppler\Library\bin",
  (Join-Path $VendorDir 'poppler\Library\bin')
) | Where-Object { Test-Path (Join-Path $_ 'pdftoppm.exe') } | Select-Object -First 1

if (-not $PopplerBin) {
  Write-Host "Poppler not found. Attempting installation..." -ForegroundColor Yellow
  
  # Method 1: Try winget
  if (Test-Command 'winget') {
    Write-Host "  Trying winget installation..." -ForegroundColor Yellow
    try {
      $wingetResult = winget install -e --id Poppler.Poppler --silent --accept-package-agreements --accept-source-agreements 2>&1
      if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Poppler installed via winget" -ForegroundColor Green
        Start-Sleep -Seconds 2  # Give installer time to complete
      }
    } catch {
      Write-Host "  ✗ winget installation failed (may need admin rights)" -ForegroundColor Yellow
    }
    
    # Check again after winget attempt
    $PopplerBin = @(
      "$Env:ProgramFiles\poppler\Library\bin",
      "$Env:ProgramFiles(x86)\poppler\Library\bin"
    ) | Where-Object { Test-Path (Join-Path $_ 'pdftoppm.exe') } | Select-Object -First 1
  }
  
  # Method 2: Download portable Poppler (fallback - always works)
  if (-not $PopplerBin) {
    Write-Host "  Downloading portable Poppler package..." -ForegroundColor Yellow
    try {
      $ReleaseUrl = 'https://github.com/oschwartz10612/poppler-windows/releases/latest/download/Release-25.07.0-0.zip'
      $ZipPath = Join-Path $VendorDir 'poppler.zip'
      $ExtractDir = Join-Path $VendorDir 'poppler'
      
      # Remove old extraction if exists
      if (Test-Path $ExtractDir) {
        Remove-Item $ExtractDir -Recurse -Force -ErrorAction SilentlyContinue
      }
      
      Write-Host "  Downloading from GitHub..." -ForegroundColor Yellow
      Invoke-WebRequest -Uri $ReleaseUrl -OutFile $ZipPath -UseBasicParsing -ErrorAction Stop
      
      Write-Host "  Extracting..." -ForegroundColor Yellow
      Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force -ErrorAction Stop
      Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
      
      # Find the bin folder
      $Candidate = Get-ChildItem -Recurse -Directory -Path $ExtractDir | Where-Object { 
        $_.Name -eq 'bin' -and (Test-Path (Join-Path $_.FullName 'pdftoppm.exe')) 
      } | Select-Object -First 1
      
      if ($Candidate) {
        $PopplerBin = $Candidate.FullName
        Write-Host "  ✓ Poppler extracted to vendor directory" -ForegroundColor Green
      }
    } catch {
      Write-Host "  ✗ Download/extraction failed: $($_.Exception.Message)" -ForegroundColor Red
      Write-Host "    This may be due to network issues or permissions." -ForegroundColor Yellow
    }
  }
}

if ($PopplerBin) {
  Write-Host "✓ Poppler found at: $PopplerBin" -ForegroundColor Green
  [Environment]::SetEnvironmentVariable('POPPLER_PATH', $PopplerBin, 'User')
  Write-Host "  Environment variable POPPLER_PATH set (restart terminal to apply)" -ForegroundColor Gray
} else {
  Write-Host "✗ Could not auto-install Poppler." -ForegroundColor Red
  Write-Host "  Manual installation options:" -ForegroundColor Yellow
  Write-Host "    1. Run as Administrator and try again" -ForegroundColor Yellow
  Write-Host "    2. Install manually: winget install -e --id Poppler.Poppler" -ForegroundColor Yellow
  Write-Host "    3. Download from: https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Installation Summary ===" -ForegroundColor Cyan
if ($TesseractExe -and $PopplerBin) {
  Write-Host "✓ Both Tesseract and Poppler are configured!" -ForegroundColor Green
  Write-Host "  Restart your terminal or log out/in to apply environment variables." -ForegroundColor Yellow
} elseif ($TesseractExe) {
  Write-Host "⚠ Tesseract configured, but Poppler is missing." -ForegroundColor Yellow
  Write-Host "  OCR will work partially - PDF conversion may fail." -ForegroundColor Yellow
} elseif ($PopplerBin) {
  Write-Host "⚠ Poppler configured, but Tesseract is missing." -ForegroundColor Yellow
  Write-Host "  OCR will work partially - text recognition may fail." -ForegroundColor Yellow
} else {
  Write-Host "✗ Neither Tesseract nor Poppler could be installed automatically." -ForegroundColor Red
  Write-Host "  Please install them manually or run this script as Administrator." -ForegroundColor Yellow
}
Write-Host ""
