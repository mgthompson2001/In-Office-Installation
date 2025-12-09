# Medisoft Billing Bot - OCR Dependencies Installer
# Installs Tesseract OCR and Poppler for PDF processing
# Can be run standalone or called from Install.bots

param(
    [Parameter(Mandatory=$false)]
    [string]$InstallDir = $PSScriptRoot
)

$ErrorActionPreference = 'Continue'

# Redirect all output to console
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Normalize the installation directory path
# Remove any surrounding quotes, trailing backslashes, and resolve to absolute path
if ($InstallDir) {
    $InstallDir = $InstallDir.Trim().Trim('"').Trim("'").TrimEnd('\').TrimEnd('/')
    try {
        # Convert to absolute path if it's relative
        if (-not [System.IO.Path]::IsPathRooted($InstallDir)) {
            $InstallDir = Resolve-Path $InstallDir -ErrorAction Stop
        } else {
            # For absolute paths, just normalize them
            $InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
        }
    } catch {
        # If resolution fails, try to use the path as-is after cleaning
        Write-Host "Warning: Could not fully resolve path: $InstallDir" -ForegroundColor Yellow
    }
} else {
    # Fallback to script's parent directory
    $InstallDir = Split-Path $PSScriptRoot -Parent
}

Write-Host "=== OCR Dependencies Installation ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will install Tesseract OCR and Poppler for PDF processing" -ForegroundColor Gray
Write-Host "Installation directory: $InstallDir" -ForegroundColor Gray
Write-Host ""
Write-Host "Updated: Path normalization fixes applied for paths with spaces" -ForegroundColor DarkGray
Write-Host ""

# Determine vendor directory (properly normalize path)
$VendorDir = Join-Path $InstallDir "vendor"
$VendorDir = [System.IO.Path]::GetFullPath($VendorDir)

# Create vendor directory if it doesn't exist
if (-not (Test-Path $VendorDir)) {
    try {
        New-Item -ItemType Directory -Force -Path $VendorDir | Out-Null
        Write-Host "Created vendor directory: $VendorDir" -ForegroundColor Gray
    } catch {
        Write-Host "Warning: Could not create vendor directory: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Helper functions
function Test-Command($name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    return $null -ne $cmd
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-Tesseract {
    Write-Host "Checking for Tesseract OCR..." -ForegroundColor Cyan
    
    # Check existing installations
    $TesseractExe = @(
        "$Env:ProgramFiles\Tesseract-OCR\tesseract.exe",
        "$Env:ProgramFiles(x86)\Tesseract-OCR\tesseract.exe",
        "$Env:LocalAppData\Programs\Tesseract-OCR\tesseract.exe",
        (Join-Path $VendorDir 'Tesseract-OCR\tesseract.exe')
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    
    if ($TesseractExe) {
        Write-Host "  ✓ Tesseract found at: $TesseractExe" -ForegroundColor Green
        [Environment]::SetEnvironmentVariable('TESSERACT_PATH', $TesseractExe, 'User')
        return $TesseractExe
    }
    
    Write-Host "  Tesseract not found. Attempting installation..." -ForegroundColor Yellow
    
    # Method 1: Try winget (if available)
    if (Test-Command 'winget') {
        Write-Host "  Trying winget installation..." -ForegroundColor Yellow
        try {
            # Try without admin first (user-level installation)
            $proc = Start-Process -FilePath "winget" -ArgumentList "install -e --id UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements --scope user" -Wait -PassThru -NoNewWindow -ErrorAction SilentlyContinue
            
            # If that fails, try with admin elevation
            if ($null -eq $proc -or $proc.ExitCode -ne 0) {
                Write-Host "    User-level installation failed, trying with elevation..." -ForegroundColor Gray
                try {
                    $proc = Start-Process -FilePath "winget" -ArgumentList "install -e --id UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements" -Wait -PassThru -Verb RunAs -NoNewWindow -ErrorAction SilentlyContinue
                } catch {
                    Write-Host "    Admin elevation failed or declined" -ForegroundColor Gray
                }
            }
            
            if ($proc -and $proc.ExitCode -eq 0) {
                Start-Sleep -Seconds 5  # Wait longer for installation to complete
                $TesseractExe = @(
                    "$Env:ProgramFiles\Tesseract-OCR\tesseract.exe",
                    "$Env:ProgramFiles(x86)\Tesseract-OCR\tesseract.exe",
                    "$Env:LocalAppData\Programs\Tesseract-OCR\tesseract.exe"
                ) | Where-Object { Test-Path $_ } | Select-Object -First 1
                if ($TesseractExe) {
                    Write-Host "  ✓ Tesseract installed via winget" -ForegroundColor Green
                    [Environment]::SetEnvironmentVariable('TESSERACT_PATH', $TesseractExe, 'User')
                    return $TesseractExe
                }
            } else {
                Write-Host "  ✗ winget installation failed (may need admin rights)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  ✗ winget installation failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    
    # Method 2: Download and install to vendor directory (no admin required)
    Write-Host "  Downloading portable Tesseract..." -ForegroundColor Yellow
    try {
        # Test network connectivity first
        $networkTest = Test-NetConnection -ComputerName "digi.bib.uni-mannheim.de" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
        if (-not $networkTest) {
            Write-Host "  ✗ Network connectivity issue - cannot download" -ForegroundColor Red
            throw "Network connection failed"
        }
        
        $TesseractUrl = 'https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe'
        $TesseractInstaller = Join-Path $env:TEMP 'tesseract-installer.exe'
        
        Write-Host "    Downloading from $TesseractUrl..." -ForegroundColor Gray
        Invoke-WebRequest -Uri $TesseractUrl -OutFile $TesseractInstaller -UseBasicParsing -TimeoutSec 120 -ErrorAction Stop
        
        Write-Host "    Download complete. Installing to vendor directory..." -ForegroundColor Gray
        $installArgs = "/S /D=$VendorDir\Tesseract-OCR"
        $proc = Start-Process -FilePath $TesseractInstaller -ArgumentList $installArgs -Wait -PassThru -NoNewWindow -ErrorAction Stop
        
        Start-Sleep -Seconds 5  # Wait longer for installation to complete
        
        $TesseractExe = Join-Path $VendorDir 'Tesseract-OCR\tesseract.exe'
        if (Test-Path $TesseractExe) {
            Write-Host "  ✓ Tesseract installed to vendor directory" -ForegroundColor Green
            [Environment]::SetEnvironmentVariable('TESSERACT_PATH', $TesseractExe, 'User')
            Remove-Item $TesseractInstaller -Force -ErrorAction SilentlyContinue
            return $TesseractExe
        }
        
        # Check standard locations after installation
        $TesseractExe = @(
            "$Env:ProgramFiles\Tesseract-OCR\tesseract.exe",
            "$Env:ProgramFiles(x86)\Tesseract-OCR\tesseract.exe"
        ) | Where-Object { Test-Path $_ } | Select-Object -First 1
        
        if ($TesseractExe) {
            Write-Host "  ✓ Tesseract installed to standard location" -ForegroundColor Green
            [Environment]::SetEnvironmentVariable('TESSERACT_PATH', $TesseractExe, 'User')
            Remove-Item $TesseractInstaller -Force -ErrorAction SilentlyContinue
            return $TesseractExe
        }
        
        Remove-Item $TesseractInstaller -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "  ✗ Download/installation failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host "  ✗ Could not install Tesseract automatically" -ForegroundColor Red
    Write-Host "    Manual installation: winget install -e --id UB-Mannheim.TesseractOCR" -ForegroundColor Yellow
    return $null
}

function Install-Poppler {
    Write-Host "Checking for Poppler..." -ForegroundColor Cyan
    
    # Check existing installations
    $PopplerBin = @(
        "$Env:ProgramFiles\poppler\Library\bin",
        "$Env:ProgramFiles(x86)\poppler\Library\bin",
        (Join-Path $VendorDir 'poppler\Library\bin')
    ) | Where-Object { Test-Path (Join-Path $_ 'pdftoppm.exe') } | Select-Object -First 1
    
    if ($PopplerBin) {
        Write-Host "  ✓ Poppler found at: $PopplerBin" -ForegroundColor Green
        [Environment]::SetEnvironmentVariable('POPPLER_PATH', $PopplerBin, 'User')
        return $PopplerBin
    }
    
    Write-Host "  Poppler not found. Attempting installation..." -ForegroundColor Yellow
    
    # Method 1: Try winget
    if (Test-Command 'winget') {
        Write-Host "  Trying winget installation..." -ForegroundColor Yellow
        try {
            # Try without admin first (user-level installation)
            $proc = Start-Process -FilePath "winget" -ArgumentList "install -e --id Poppler.Poppler --silent --accept-package-agreements --accept-source-agreements --scope user" -Wait -PassThru -NoNewWindow -ErrorAction SilentlyContinue
            
            # If that fails, try with admin elevation
            if ($null -eq $proc -or $proc.ExitCode -ne 0) {
                Write-Host "    User-level installation failed, trying with elevation..." -ForegroundColor Gray
                try {
                    $proc = Start-Process -FilePath "winget" -ArgumentList "install -e --id Poppler.Poppler --silent --accept-package-agreements --accept-source-agreements" -Wait -PassThru -Verb RunAs -NoNewWindow -ErrorAction SilentlyContinue
                } catch {
                    Write-Host "    Admin elevation failed or declined" -ForegroundColor Gray
                }
            }
            
            if ($proc -and $proc.ExitCode -eq 0) {
                Start-Sleep -Seconds 5  # Wait longer for installation to complete
                $PopplerBin = @(
                    "$Env:ProgramFiles\poppler\Library\bin",
                    "$Env:ProgramFiles(x86)\poppler\Library\bin",
                    "$Env:LocalAppData\Programs\poppler\Library\bin"
                ) | Where-Object { Test-Path (Join-Path $_ 'pdftoppm.exe') } | Select-Object -First 1
                if ($PopplerBin) {
                    Write-Host "  ✓ Poppler installed via winget" -ForegroundColor Green
                    [Environment]::SetEnvironmentVariable('POPPLER_PATH', $PopplerBin, 'User')
                    return $PopplerBin
                }
            } else {
                Write-Host "  ✗ winget installation failed (may need admin rights)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  ✗ winget installation failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    
    # Method 2: Download portable version to vendor directory (no admin required)
    Write-Host "  Downloading portable Poppler from GitHub..." -ForegroundColor Yellow
    $ZipPath = Join-Path $env:TEMP 'poppler.zip'
    $ExtractDir = Join-Path $VendorDir 'poppler'
    
    # Normalize paths
    $ZipPath = [System.IO.Path]::GetFullPath($ZipPath)
    $ExtractDir = [System.IO.Path]::GetFullPath($ExtractDir)
    
    try {
        # Test network connectivity first
        Write-Host "    Checking network connectivity..." -ForegroundColor Gray
        try {
            $networkTest = Test-NetConnection -ComputerName "github.com" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction Stop
            if (-not $networkTest) {
                throw "Cannot reach github.com on port 443"
            }
        } catch {
            Write-Host "    ⚠ Network test failed, but attempting download anyway..." -ForegroundColor Yellow
        }
        
        # Clean up any existing extraction
        if (Test-Path $ExtractDir) {
            Remove-Item $ExtractDir -Recurse -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path $ZipPath) {
            Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
        }
        
        # Get the latest release URL dynamically using GitHub API
        Write-Host "    Finding latest Poppler release..." -ForegroundColor Gray
        $ReleaseUrl = $null
        
        # Try method 1: Use GitHub API to get latest release
        try {
            $ProgressPreference = 'SilentlyContinue'
            $apiUrl = 'https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest'
            Write-Host "    Querying GitHub API..." -ForegroundColor Gray
            $releaseInfo = Invoke-RestMethod -Uri $apiUrl -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
            $zipAsset = $releaseInfo.assets | Where-Object { $_.name -like 'Release-*.zip' } | Select-Object -First 1
            if ($zipAsset) {
                $ReleaseUrl = $zipAsset.browser_download_url
                Write-Host "    Found latest release: $($releaseInfo.tag_name)" -ForegroundColor Gray
            }
        } catch {
            Write-Host "    ⚠ API method failed, trying direct URLs..." -ForegroundColor Yellow
        }
        
        # Try method 2: Try known working release URLs (using version-specific paths, not /latest/download/)
        if (-not $ReleaseUrl) {
            Write-Host "    Trying known release URLs..." -ForegroundColor Gray
            $commonUrls = @(
                'https://github.com/oschwartz10612/poppler-windows/releases/download/v25.11.0-0/Release-25.11.0-0.zip',
                'https://github.com/oschwartz10612/poppler-windows/releases/download/v25.07.0-0/Release-25.07.0-0.zip',
                'https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip',
                'https://github.com/oschwartz10612/poppler-windows/releases/download/v23.11.0-0/Release-23.11.0-0.zip'
            )
            
            foreach ($url in $commonUrls) {
                try {
                    Write-Host "      Testing: $url" -ForegroundColor DarkGray
                    $response = Invoke-WebRequest -Uri $url -Method Head -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
                    if ($response.StatusCode -eq 200) {
                        $ReleaseUrl = $url
                        Write-Host "    Found working URL" -ForegroundColor Gray
                        break
                    }
                } catch {
                    continue
                }
            }
        }
        
        if (-not $ReleaseUrl) {
            throw "Could not find a valid Poppler release URL. Check network connectivity and GitHub availability."
        }
        
        Write-Host "    Downloading from: $ReleaseUrl" -ForegroundColor Gray
        
        # Download with retry
        $downloadSuccess = $false
        $maxRetries = 3
        for ($retry = 1; $retry -le $maxRetries; $retry++) {
            try {
                if ($retry -gt 1) {
                    Write-Host "    Retry attempt $retry of $maxRetries..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 2
                }
                
                $ProgressPreference = 'SilentlyContinue'
                Invoke-WebRequest -Uri $ReleaseUrl -OutFile $ZipPath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop
                
                # Verify download
                if (-not (Test-Path $ZipPath)) {
                    throw "Downloaded file not found: $ZipPath"
                }
                
                $fileSize = (Get-Item $ZipPath).Length
                if ($fileSize -lt 1048576) {  # Less than 1MB seems suspicious
                    throw "Downloaded file seems too small ($([math]::Round($fileSize / 1MB, 2)) MB) - may be corrupted"
                }
                
                Write-Host "    ✓ Download complete ($([math]::Round($fileSize / 1MB, 2)) MB)" -ForegroundColor Green
                $downloadSuccess = $true
                break
            } catch {
                if ($retry -eq $maxRetries) {
                    throw "Download failed after $maxRetries attempts: $($_.Exception.Message)"
                }
                Write-Host "    Download attempt $retry failed: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
        
        if (-not $downloadSuccess) {
            throw "Download failed after all retry attempts"
        }
        
        # Extract archive
        Write-Host "    Extracting archive..." -ForegroundColor Gray
        try {
            Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force -ErrorAction Stop
        } catch {
            # Try using .NET extraction as fallback
            Write-Host "    PowerShell extraction failed, trying .NET method..." -ForegroundColor Yellow
            try {
                Add-Type -AssemblyName System.IO.Compression.FileSystem
                [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $ExtractDir)
            } catch {
                throw "Extraction failed with both methods: $($_.Exception.Message)"
            }
        }
        
        Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
        
        # Find pdftoppm.exe
        Write-Host "    Searching for pdftoppm.exe..." -ForegroundColor Gray
        $pdftoppmFile = Get-ChildItem -Recurse -Path $ExtractDir -Filter 'pdftoppm.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
        
        if ($pdftoppmFile) {
            $PopplerBin = $pdftoppmFile.DirectoryName
            Write-Host "  ✓ Poppler extracted successfully" -ForegroundColor Green
            Write-Host "    Location: $PopplerBin" -ForegroundColor Gray
            try {
                [Environment]::SetEnvironmentVariable('POPPLER_PATH', $PopplerBin, 'User')
                Write-Host "  ✓ Environment variable set" -ForegroundColor Green
            } catch {
                Write-Host "  ⚠ Could not set environment variable: $($_.Exception.Message)" -ForegroundColor Yellow
            }
            return $PopplerBin
        } else {
            throw "Could not find pdftoppm.exe in extracted archive. Archive structure may have changed."
        }
        
    } catch {
        $errorMsg = $_.Exception.Message
        if ($_.Exception.InnerException) {
            $errorMsg += " | Inner: $($_.Exception.InnerException.Message)"
        }
        # Also write to error stream to ensure it's visible
        Write-Error "Poppler installation failed: $errorMsg" -ErrorAction Continue
        Write-Host "  [ERROR] Poppler installation failed: $errorMsg" -ForegroundColor Red
        Write-Host "    Troubleshooting steps:" -ForegroundColor Yellow
        Write-Host "      1. Check network connectivity to github.com" -ForegroundColor Yellow
        Write-Host "      2. Check firewall/antivirus isn't blocking downloads" -ForegroundColor Yellow
        Write-Host "      3. Verify sufficient disk space in: $env:TEMP" -ForegroundColor Yellow
        Write-Host "      4. Try manual installation as Administrator:" -ForegroundColor Yellow
        Write-Host "         winget install -e --id Poppler.Poppler" -ForegroundColor Cyan
        Write-Host "      5. Or download manually from:" -ForegroundColor Yellow
        Write-Host "         https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Cyan
        
        # Write detailed error to temp file for debugging
        $errorLog = Join-Path $env:TEMP "poppler_install_error_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
        try {
            @"
Poppler Installation Error Report
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

Error Message: $errorMsg
Exception Type: $($_.Exception.GetType().FullName)
Stack Trace: $($_.Exception.StackTrace)

Installation Directory: $InstallDir
Vendor Directory: $VendorDir
Temp Directory: $env:TEMP
Zip Path: $ZipPath
Extract Directory: $ExtractDir

Network Test: $(try { Test-NetConnection -ComputerName "github.com" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue } catch { "Failed" })
Disk Space (Temp): $([math]::Round((Get-PSDrive $env:TEMP[0]).Free / 1GB, 2)) GB free

"@ | Out-File -FilePath $errorLog -Encoding UTF8
            Write-Host "    Detailed error log saved to: $errorLog" -ForegroundColor Gray
        } catch {
            # Ignore if we can't write the log
        }
    }
    
    Write-Host "  [FAIL] Could not install Poppler automatically" -ForegroundColor Red
    Write-Host "    Manual installation required: winget install -e --id Poppler.Poppler" -ForegroundColor Yellow
    return $null
}

# Main installation
Write-Host "Starting OCR dependencies installation..." -ForegroundColor Cyan
Write-Host ""

$TesseractExe = Install-Tesseract
Write-Host ""

$PopplerBin = Install-Poppler
Write-Host ""

# Summary
Write-Host "=== Installation Summary ===" -ForegroundColor Cyan
Write-Host ""

if ($TesseractExe -and $PopplerBin) {
    Write-Host "✓ Both Tesseract and Poppler are configured!" -ForegroundColor Green
    Write-Host "  Tesseract: $TesseractExe" -ForegroundColor Gray
    Write-Host "  Poppler: $PopplerBin" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  NOTE: You may need to restart your terminal or log out/in" -ForegroundColor Yellow
    Write-Host "  for environment variables to take effect." -ForegroundColor Yellow
    exit 0
} elseif ($TesseractExe) {
    Write-Host "[FAIL] Tesseract configured, but Poppler installation FAILED." -ForegroundColor Red
    Write-Host "  Tesseract: $TesseractExe" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Poppler is REQUIRED for full functionality." -ForegroundColor Red
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "  1. Internet connectivity" -ForegroundColor Yellow
    Write-Host "  2. Firewall/antivirus blocking downloads" -ForegroundColor Yellow
    Write-Host "  3. Sufficient disk space" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Manual installation options:" -ForegroundColor Yellow
    Write-Host "  - As Administrator: winget install -e --id Poppler.Poppler" -ForegroundColor Cyan
    Write-Host "  - Or download from: https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Cyan
    exit 1
} elseif ($PopplerBin) {
    Write-Host "⚠ Poppler configured, but Tesseract is missing." -ForegroundColor Yellow
    Write-Host "  Poppler: $PopplerBin" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  OCR will work partially - text recognition may fail." -ForegroundColor Yellow
    Write-Host "  To install Tesseract manually:" -ForegroundColor Yellow
    Write-Host "    winget install -e --id UB-Mannheim.TesseractOCR" -ForegroundColor Cyan
    Write-Host "    Or download from: https://github.com/tesseract-ocr/tesseract/wiki" -ForegroundColor Cyan
    exit 1
} else {
    Write-Host "✗ Neither Tesseract nor Poppler could be installed automatically." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Manual installation options:" -ForegroundColor Yellow
    Write-Host "    1. Run this installer as Administrator" -ForegroundColor Yellow
    Write-Host "    2. Install via winget (run as Administrator):" -ForegroundColor Yellow
    Write-Host "       winget install -e --id UB-Mannheim.TesseractOCR" -ForegroundColor Cyan
    Write-Host "       winget install -e --id Poppler.Poppler" -ForegroundColor Cyan
    Write-Host "    3. Download and install manually:" -ForegroundColor Yellow
    Write-Host "       Tesseract: https://github.com/tesseract-ocr/tesseract/wiki" -ForegroundColor Cyan
    Write-Host "       Poppler: https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Cyan
    exit 2
}

