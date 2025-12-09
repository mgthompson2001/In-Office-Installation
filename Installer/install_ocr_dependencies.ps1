# OCR Dependencies Installer
# Installs Tesseract OCR and Poppler for PDF processing
# Universal installation for all employee computers

param(
    [Parameter(Mandatory=$false)]
    [string]$InstallDir = ""
)

$ErrorActionPreference = 'Continue'

# Normalize the installation directory path
# Remove any surrounding quotes, trailing backslashes, and resolve to absolute path
if ([string]::IsNullOrEmpty($InstallDir)) {
    # If InstallDir not provided, use parent of Installer folder
    $InstallDir = Split-Path -Parent $PSScriptRoot
} else {
    # Clean and normalize the provided path
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
}

Write-Host "=== OCR Dependencies Installation ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installation directory: $InstallDir" -ForegroundColor Gray
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

# Helper function to test if command exists
function Test-Command {
    param([string]$name)
    try {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        return ($null -ne $cmd)
    } catch {
        return $false
    }
}

# Install Tesseract OCR
function Install-Tesseract {
    Write-Host "Checking for Tesseract OCR..." -ForegroundColor Cyan
    
    # Check existing installations (check LocalAppData first as that's where winget installs)
    $TesseractExe = $null
    $checkPaths = @(
        "$Env:LocalAppData\Programs\Tesseract-OCR\tesseract.exe",
        "$Env:ProgramFiles\Tesseract-OCR\tesseract.exe",
        "${Env:ProgramFiles(x86)}\Tesseract-OCR\tesseract.exe",
        (Join-Path $VendorDir 'Tesseract-OCR\tesseract.exe')
    )
    
    foreach ($path in $checkPaths) {
        if (Test-Path $path) {
            $TesseractExe = $path
            break
        }
    }
    
    if ($TesseractExe) {
        Write-Host "  Tesseract found at: $TesseractExe" -ForegroundColor Green
        try {
            [Environment]::SetEnvironmentVariable('TESSERACT_PATH', $TesseractExe, 'User')
        } catch {
            Write-Host "  Could not set environment variable" -ForegroundColor Yellow
        }
        return $TesseractExe
    }
    
    Write-Host "  Tesseract not found. Attempting installation..." -ForegroundColor Yellow
    
    # Method 1: Try winget
    if (Test-Command 'winget') {
        Write-Host "  Trying winget installation..." -ForegroundColor Yellow
        try {
            $proc = Start-Process -FilePath "winget" -ArgumentList "install -e --id UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements" -Wait -PassThru -NoNewWindow
            if ($proc.ExitCode -eq 0) {
                Start-Sleep -Seconds 3
                # Check all paths, starting with LocalAppData (where winget installs)
                foreach ($path in $checkPaths) {
                    if (Test-Path $path) {
                        $TesseractExe = $path
                        Write-Host "  Tesseract installed via winget" -ForegroundColor Green
                        Write-Host "    Location: $TesseractExe" -ForegroundColor Gray
                        try {
                            [Environment]::SetEnvironmentVariable('TESSERACT_PATH', $TesseractExe, 'User')
                        } catch {
                            Write-Host "  Could not set environment variable" -ForegroundColor Yellow
                        }
                        return $TesseractExe
                    }
                }
            }
        } catch {
            Write-Host "  winget installation failed" -ForegroundColor Yellow
        }
    }
    
    # Method 2: Download portable version
    Write-Host "  Downloading portable Tesseract..." -ForegroundColor Yellow
    try {
        $TesseractUrl = 'https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe'
        $TesseractInstaller = Join-Path $env:TEMP 'tesseract-installer.exe'
        
        Write-Host "  Downloading installer..." -ForegroundColor Gray
        Invoke-WebRequest -Uri $TesseractUrl -OutFile $TesseractInstaller -UseBasicParsing -TimeoutSec 300
        
        Write-Host "  Installing to vendor directory..." -ForegroundColor Gray
        $installTarget = Join-Path $VendorDir "Tesseract-OCR"
        $installArgs = "/S /D=$installTarget"
        Start-Process -FilePath $TesseractInstaller -ArgumentList $installArgs -Wait -NoNewWindow
        
        Start-Sleep -Seconds 2
        
        $TesseractExe = Join-Path $VendorDir 'Tesseract-OCR\tesseract.exe'
        if (Test-Path $TesseractExe) {
            Write-Host "  Tesseract installed to vendor directory" -ForegroundColor Green
            try {
                [Environment]::SetEnvironmentVariable('TESSERACT_PATH', $TesseractExe, 'User')
            } catch {
                Write-Host "  Could not set environment variable" -ForegroundColor Yellow
            }
            Remove-Item $TesseractInstaller -Force -ErrorAction SilentlyContinue
            return $TesseractExe
        }
        
        Remove-Item $TesseractInstaller -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "  Download/installation failed" -ForegroundColor Yellow
    }
    
    Write-Host "  Could not install Tesseract automatically" -ForegroundColor Yellow
    return $null
}

# Install Poppler
function Install-Poppler {
    Write-Host "Checking for Poppler..." -ForegroundColor Cyan
    
    # Check existing installations
    $PopplerBin = $null
    $checkPaths = @(
        "$Env:LocalAppData\poppler\Library\bin",
        "$Env:ProgramFiles\poppler\Library\bin",
        "${Env:ProgramFiles(x86)}\poppler\Library\bin",
        (Join-Path $VendorDir 'poppler\Library\bin')
    )
    
    foreach ($path in $checkPaths) {
        $pdftoppm = Join-Path $path 'pdftoppm.exe'
        if (Test-Path $pdftoppm) {
            $PopplerBin = $path
            break
        }
    }
    
    if ($PopplerBin) {
        Write-Host "  Poppler found at: $PopplerBin" -ForegroundColor Green
        try {
            [Environment]::SetEnvironmentVariable('POPPLER_PATH', $PopplerBin, 'User')
        } catch {
            Write-Host "  Could not set environment variable" -ForegroundColor Yellow
        }
        return $PopplerBin
    }
    
    Write-Host "  Poppler not found. Attempting installation..." -ForegroundColor Yellow
    
    # Method 1: Try winget (multiple package IDs)
    if (Test-Command 'winget') {
        Write-Host "  Trying winget installation..." -ForegroundColor Yellow
        $wingetPackages = @('Poppler.Poppler', 'poppler', 'Poppler')
        
        foreach ($packageId in $wingetPackages) {
            try {
                Write-Host "    Trying package: $packageId" -ForegroundColor Gray
                # Search for the package first
                $searchResult = & winget search $packageId 2>&1
                if ($LASTEXITCODE -eq 0 -and $searchResult -match 'poppler') {
                    # Try user-level install first
                    $proc = Start-Process -FilePath "winget" -ArgumentList "install -e --id $packageId --silent --accept-package-agreements --accept-source-agreements --scope user" -Wait -PassThru -NoNewWindow -ErrorAction SilentlyContinue
                    
                    # If that fails, try system-level (may require admin)
                    if ($null -eq $proc -or $proc.ExitCode -ne 0) {
                        Write-Host "    User-level install failed, trying system-level..." -ForegroundColor Gray
                        $proc = Start-Process -FilePath "winget" -ArgumentList "install -e --id $packageId --silent --accept-package-agreements --accept-source-agreements" -Wait -PassThru -NoNewWindow -ErrorAction SilentlyContinue
                    }
                    
                    if ($proc -and $proc.ExitCode -eq 0) {
                        Start-Sleep -Seconds 5
                        # Check all paths, starting with LocalAppData
                        foreach ($path in $checkPaths) {
                            $pdftoppm = Join-Path $path 'pdftoppm.exe'
                            if (Test-Path $pdftoppm) {
                                $PopplerBin = $path
                                Write-Host "  ✓ Poppler installed via winget" -ForegroundColor Green
                                try {
                                    [Environment]::SetEnvironmentVariable('POPPLER_PATH', $PopplerBin, 'User')
                                } catch {
                                    Write-Host "  ⚠ Could not set environment variable" -ForegroundColor Yellow
                                }
                                return $PopplerBin
                            }
                        }
                    }
                }
            } catch {
                # Continue to next package ID
                continue
            }
        }
        Write-Host "  winget installation not successful, trying alternative methods..." -ForegroundColor Yellow
    }
    
    # Method 1b: Try Chocolatey if available
    if (Test-Command 'choco') {
        Write-Host "  Trying Chocolatey installation..." -ForegroundColor Yellow
        try {
            $proc = Start-Process -FilePath "choco" -ArgumentList "install poppler -y" -Wait -PassThru -NoNewWindow -ErrorAction SilentlyContinue
            if ($proc -and $proc.ExitCode -eq 0) {
                Start-Sleep -Seconds 3
                # Check all paths, starting with LocalAppData
                foreach ($path in $checkPaths) {
                    $pdftoppm = Join-Path $path 'pdftoppm.exe'
                    if (Test-Path $pdftoppm) {
                        $PopplerBin = $path
                        Write-Host "  ✓ Poppler installed via Chocolatey" -ForegroundColor Green
                        try {
                            [Environment]::SetEnvironmentVariable('POPPLER_PATH', $PopplerBin, 'User')
                        } catch {
                            Write-Host "  ⚠ Could not set environment variable" -ForegroundColor Yellow
                        }
                        return $PopplerBin
                    }
                }
            }
        } catch {
            Write-Host "  Chocolatey installation failed" -ForegroundColor Yellow
        }
    }
    
    # Method 2: Download portable version from GitHub
    Write-Host "  Downloading portable Poppler from GitHub..." -ForegroundColor Yellow
    $ZipPath = Join-Path $env:TEMP 'poppler.zip'
    # Install to AppData\Local\poppler (standard location that bot checks)
    $ExtractDir = "$Env:LocalAppData\poppler"
    
    # Ensure paths are normalized
    $ZipPath = [System.IO.Path]::GetFullPath($ZipPath)
    $ExtractDir = [System.IO.Path]::GetFullPath($ExtractDir)
    
    try {
        # Clean up any existing extraction
        if (Test-Path $ExtractDir) {
            Remove-Item $ExtractDir -Recurse -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path $ZipPath) {
            Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
        }
        
        # Get the latest release URL dynamically
        Write-Host "  Finding latest Poppler release..." -ForegroundColor Gray
        $ReleaseUrl = $null
        
        # Try method 1: Use GitHub API to get latest release
        try {
            $apiUrl = 'https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest'
            $releaseInfo = Invoke-RestMethod -Uri $apiUrl -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
            $zipAsset = $releaseInfo.assets | Where-Object { $_.name -like 'Release-*.zip' } | Select-Object -First 1
            if ($zipAsset) {
                $ReleaseUrl = $zipAsset.browser_download_url
                Write-Host "  Found latest release: $($releaseInfo.tag_name)" -ForegroundColor Gray
            }
        } catch {
            Write-Host "  API method failed, trying direct URL..." -ForegroundColor Gray
        }
        
        # Try method 2: Try common latest release patterns (use specific version URL)
        if (-not $ReleaseUrl) {
            $commonUrls = @(
                'https://github.com/oschwartz10612/poppler-windows/releases/download/v25.07.0-0/Release-25.07.0-0.zip',
                'https://github.com/oschwartz10612/poppler-windows/releases/latest/download/Release-25.07.0-0.zip',
                'https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip'
            )
            
            foreach ($url in $commonUrls) {
                try {
                    Write-Host "  Trying: $url" -ForegroundColor Gray
                    $response = Invoke-WebRequest -Uri $url -Method Head -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
                    if ($response.StatusCode -eq 200) {
                        $ReleaseUrl = $url
                        break
                    }
                } catch {
                    continue
                }
            }
        }
        
        if (-not $ReleaseUrl) {
            throw "Could not find a valid Poppler release URL"
        }
        
        Write-Host "  Downloading from: $ReleaseUrl" -ForegroundColor Gray
        
        # Download with progress
        $ProgressPreference = 'SilentlyContinue'
        try {
            Invoke-WebRequest -Uri $ReleaseUrl -OutFile $ZipPath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop
        } catch {
            # Retry once with different settings
            Write-Host "  Download failed, retrying..." -ForegroundColor Yellow
            Start-Sleep -Seconds 2
            Invoke-WebRequest -Uri $ReleaseUrl -OutFile $ZipPath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop
        }
        
        if (-not (Test-Path $ZipPath)) {
            throw "Downloaded file not found: $ZipPath"
        }
        
        $fileSize = (Get-Item $ZipPath).Length / 1MB
        if ($fileSize -lt 1) {
            throw "Downloaded file seems too small ($([math]::Round($fileSize, 2)) MB) - may be corrupted"
        }
        
        Write-Host "  ✓ Download complete ($([math]::Round($fileSize, 2)) MB)" -ForegroundColor Green
        
        Write-Host "  Extracting archive..." -ForegroundColor Gray
        try {
            Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force -ErrorAction Stop
        } catch {
            Write-Host "  Extraction failed: $($_.Exception.Message)" -ForegroundColor Red
            # Try using .NET extraction as fallback
            Write-Host "  Trying alternative extraction method..." -ForegroundColor Yellow
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $ExtractDir)
        }
        
        Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
        
        # Find the bin folder - search more broadly
        Write-Host "  Searching for pdftoppm.exe..." -ForegroundColor Gray
        $pdftoppmFile = Get-ChildItem -Recurse -Path $ExtractDir -Filter 'pdftoppm.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
        
        if ($pdftoppmFile) {
            $PopplerBin = $pdftoppmFile.DirectoryName
            
            # If extracted to a subdirectory (like Release-25.07.0-0\poppler-25.07.0\Library\bin),
            # move it to the expected location
            $expectedBinPath = Join-Path $ExtractDir 'Library\bin'
            if ($PopplerBin -ne $expectedBinPath) {
                Write-Host "  Reorganizing Poppler structure..." -ForegroundColor Gray
                # Find the root poppler folder in the extracted directory
                $popplerRoot = Get-ChildItem -Path $ExtractDir -Directory | Where-Object { 
                    (Test-Path (Join-Path $_.FullName 'Library\bin\pdftoppm.exe'))
                } | Select-Object -First 1
                
                if ($popplerRoot) {
                    # Remove existing target if it exists
                    if (Test-Path $ExtractDir) {
                        Remove-Item $ExtractDir -Recurse -Force -ErrorAction SilentlyContinue
                    }
                    # Move the poppler folder to the expected location
                    Move-Item $popplerRoot.FullName $ExtractDir -Force
                    $PopplerBin = $expectedBinPath
                }
            }
            
            Write-Host "  ✓ Poppler extracted successfully" -ForegroundColor Green
            Write-Host "    Location: $PopplerBin" -ForegroundColor Gray
            try {
                [Environment]::SetEnvironmentVariable('POPPLER_PATH', $PopplerBin, 'User')
                Write-Host "  ✓ Environment variable set" -ForegroundColor Green
            } catch {
                Write-Host "  ⚠ Could not set environment variable: $($_.Exception.Message)" -ForegroundColor Yellow
                Write-Host "    You may need to set POPPLER_PATH manually" -ForegroundColor Yellow
            }
            return $PopplerBin
        } else {
            throw "Could not find pdftoppm.exe in extracted archive at: $ExtractDir"
        }
    } catch {
        Write-Host "  ✗ Poppler installation failed: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.InnerException) {
            Write-Host "    Details: $($_.Exception.InnerException.Message)" -ForegroundColor Red
        }
        
        # Cleanup on failure
        if (Test-Path $ZipPath) {
            Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path $ExtractDir) {
            Remove-Item $ExtractDir -Recurse -Force -ErrorAction SilentlyContinue
        }
        
        throw
    }
    
    # If we get here, all installation methods failed
    Write-Host "  ✗ All Poppler installation methods failed" -ForegroundColor Red
    throw "Poppler installation failed. All installation methods (winget, Chocolatey, GitHub download) were unsuccessful. Please check network connectivity and try manual installation."
}

# Main installation
try {
    Write-Host "Installation directory: $InstallDir" -ForegroundColor Gray
    Write-Host "Vendor directory: $VendorDir" -ForegroundColor Gray
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
        exit 0
    } elseif ($TesseractExe) {
        Write-Host "✗ Tesseract configured, but Poppler installation FAILED." -ForegroundColor Red
        Write-Host "  Tesseract: $TesseractExe" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Poppler is REQUIRED for full functionality." -ForegroundColor Red
        Write-Host "Please check:" -ForegroundColor Yellow
        Write-Host "  1. Internet connectivity" -ForegroundColor Yellow
        Write-Host "  2. Firewall/antivirus blocking downloads" -ForegroundColor Yellow
        Write-Host "  3. Sufficient disk space" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "You can try installing Poppler manually:" -ForegroundColor Yellow
        Write-Host "  winget install Poppler.Poppler" -ForegroundColor Cyan
        Write-Host "  Or download from: https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Cyan
        exit 1
    } elseif ($PopplerBin) {
        Write-Host "✗ Poppler configured, but Tesseract installation FAILED." -ForegroundColor Red
        Write-Host "  Poppler: $PopplerBin" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Tesseract is REQUIRED for OCR functionality." -ForegroundColor Red
        Write-Host "Please check installation logs above for details." -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "✗ Neither Tesseract nor Poppler could be installed automatically." -ForegroundColor Red
        Write-Host ""
        Write-Host "Both are REQUIRED for full OCR functionality." -ForegroundColor Red
        Write-Host "Please check installation logs above for details." -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "✗ Error during OCR installation: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.InnerException) {
        Write-Host "  Details: $($_.Exception.InnerException.Message)" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "OCR dependencies are REQUIRED. Installation cannot proceed." -ForegroundColor Red
    exit 1
}
