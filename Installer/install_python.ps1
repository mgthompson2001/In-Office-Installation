# Medisoft Billing Bot - Python Installation Script
# Automatically installs Python 3.11 if needed or if current version is incompatible

param(
    [Parameter(Mandatory=$false)]
    [string]$PreferredVersion = "3.11.10"
)

$ErrorActionPreference = 'Continue'

Write-Host "=== Python Installation Check ===" -ForegroundColor Cyan
Write-Host ""

# Check if Python is already installed and compatible
$PythonExe = $null
$PythonVersion = $null
$PythonCmd = $null

# Try different Python commands
$commands = @('python', 'python3', 'py')

foreach ($cmd in $commands) {
    try {
        $versionOutput = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $PythonCmd = $cmd
            $PythonExe = (Get-Command $cmd -ErrorAction SilentlyContinue).Source
            if ($versionOutput -match 'Python (\d+)\.(\d+)\.(\d+)') {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]
                $PythonVersion = "$major.$minor"
                break
            }
        }
    } catch {
        continue
    }
}

# Check if Python is compatible (3.7 - 3.12)
$IsCompatible = $false
if ($PythonVersion) {
    $major, $minor = $PythonVersion -split '\.'
    $majorNum = [int]$major
    $minorNum = [int]$minor
    
    if ($majorNum -eq 3 -and $minorNum -ge 7 -and $minorNum -le 12) {
        $IsCompatible = $true
        Write-Host "✓ Python $PythonVersion found and compatible" -ForegroundColor Green
        Write-Host "  Location: $PythonExe" -ForegroundColor Gray
        exit 0
    } else {
        Write-Host "⚠ Python $PythonVersion found but not compatible" -ForegroundColor Yellow
        Write-Host "  Required: Python 3.7 - 3.12" -ForegroundColor Gray
        Write-Host "  Recommended: Python 3.10 or 3.11" -ForegroundColor Gray
    }
} else {
    Write-Host "✗ Python not found" -ForegroundColor Red
}

# Need to install Python
Write-Host ""
Write-Host "Installing Python $PreferredVersion..." -ForegroundColor Cyan
Write-Host ""

# Determine download URL for Python 3.11.10 (latest stable 3.11.x)
$PythonVersion = $PreferredVersion
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$PythonInstaller = Join-Path $env:TEMP "python-installer.exe"

# Test network connectivity first
Write-Host "Checking network connectivity..." -ForegroundColor Gray
try {
    $networkTest = Test-NetConnection -ComputerName "www.python.org" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
    if (-not $networkTest) {
        Write-Host "  ✗ Network connectivity issue - cannot download Python" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please install Python manually:" -ForegroundColor Yellow
        Write-Host "  1. Download from: https://www.python.org/downloads/" -ForegroundColor Cyan
        Write-Host "  2. Select Python 3.10 or 3.11" -ForegroundColor Cyan
        Write-Host "  3. Check 'Add Python to PATH' during installation" -ForegroundColor Cyan
        exit 1
    }
} catch {
    Write-Host "  ⚠ Could not verify network connectivity, attempting download anyway..." -ForegroundColor Yellow
}

# Download Python installer
Write-Host "Downloading Python $PythonVersion..." -ForegroundColor Yellow
Write-Host "  This may take a few minutes depending on your connection..." -ForegroundColor Gray
try {
    Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonInstaller -UseBasicParsing -TimeoutSec 300 -ErrorAction Stop
    Write-Host "  ✓ Download complete" -ForegroundColor Green
    
    # Verify download succeeded
    if (-not (Test-Path $PythonInstaller) -or (Get-Item $PythonInstaller).Length -lt 1MB) {
        throw "Download file is invalid or too small"
    }
} catch {
    Write-Host "  ✗ Download failed: $($_.Exception.Message)" -ForegroundColor Red
    if (Test-Path $PythonInstaller) {
        Remove-Item $PythonInstaller -Force -ErrorAction SilentlyContinue
    }
    Write-Host ""
    Write-Host "Please install Python manually:" -ForegroundColor Yellow
    Write-Host "  1. Download from: https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host "  2. Select Python 3.10 or 3.11" -ForegroundColor Cyan
    Write-Host "  3. Check 'Add Python to PATH' during installation" -ForegroundColor Cyan
    exit 1
}

# Install Python silently with PATH addition
Write-Host "Installing Python $PythonVersion..." -ForegroundColor Yellow
Write-Host "  This may take a few minutes..." -ForegroundColor Gray

$installArgs = @(
    "/quiet",
    "InstallAllUsers=1",
    "PrependPath=1",
    "Include_test=0",
    "Include_pip=1",
    "Include_doc=0",
    "Include_launcher=1",
    "AssociateFiles=0",
    "Shortcuts=0"
)

try {
    $proc = Start-Process -FilePath $PythonInstaller -ArgumentList $installArgs -Wait -PassThru -NoNewWindow
    
    # Clean up installer
    Remove-Item $PythonInstaller -Force -ErrorAction SilentlyContinue
    
    if ($proc.ExitCode -eq 0) {
        Write-Host "  ✓ Installation complete" -ForegroundColor Green
        
        # Wait for installation to fully complete (longer wait for reliability)
        Start-Sleep -Seconds 10
        
        # Refresh PATH from registry (multiple methods for reliability)
        try {
            # Method 1: Refresh from registry
            $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
            $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
            $env:Path = "$machinePath;$userPath"
        } catch {
            Write-Host "  ⚠ Could not refresh PATH from registry" -ForegroundColor Yellow
        }
        
        # Method 2: Force refresh environment variables
        try {
            # Refresh current process environment
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Process")
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        } catch {
            Write-Host "  ⚠ Could not fully refresh PATH" -ForegroundColor Yellow
        }
        
        # Wait a moment for PATH to propagate
        Start-Sleep -Seconds 5
        
        # Verify installation
        Write-Host ""
        Write-Host "Verifying installation..." -ForegroundColor Cyan
        
        # Try to find newly installed Python
        $PythonPaths = @(
            "C:\Program Files\Python$PythonVersion\python.exe",
            "C:\Program Files (x86)\Python$PythonVersion\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python$PythonVersion\python.exe"
        )
        
        $found = $false
        foreach ($path in $PythonPaths) {
            if (Test-Path $path) {
                $versionOutput = & $path --version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  ✓ Python installed at: $path" -ForegroundColor Green
                    Write-Host "  Version: $versionOutput" -ForegroundColor Gray
                    $found = $true
                    break
                }
            }
        }
        
        if (-not $found) {
            # Try python command
            $versionOutput = & python --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ Python found in PATH: $versionOutput" -ForegroundColor Green
                Write-Host ""
                Write-Host "Python installation successful!" -ForegroundColor Green
                exit 0
            }
        }
        
        # Even if not immediately in PATH, installation succeeded
        # The batch file will handle PATH refresh and retry
        Write-Host ""
        Write-Host "⚠ Python installed but may need PATH refresh" -ForegroundColor Yellow
        Write-Host "  Installation succeeded, but PATH may need to be refreshed" -ForegroundColor Yellow
        Write-Host "  The installer will attempt to refresh PATH and continue" -ForegroundColor Yellow
        exit 0  # Exit 0 = success (Python was installed, just not in PATH yet)
        
    } else {
        Write-Host "  ✗ Installation failed (exit code: $($proc.ExitCode))" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please install Python manually:" -ForegroundColor Yellow
        Write-Host "  1. Download from: https://www.python.org/downloads/" -ForegroundColor Cyan
        Write-Host "  2. Select Python 3.10 or 3.11" -ForegroundColor Cyan
        Write-Host "  3. Check 'Add Python to PATH' during installation" -ForegroundColor Cyan
        exit 1
    }
} catch {
    Write-Host "  ✗ Installation error: $($_.Exception.Message)" -ForegroundColor Red
    Remove-Item $PythonInstaller -Force -ErrorAction SilentlyContinue
    exit 1
}

