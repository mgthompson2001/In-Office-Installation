# Script to install Git and set up the repository
# Run this as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git Installation and Repository Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠ This script needs Administrator privileges to install Git." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Right-click PowerShell" -ForegroundColor White
    Write-Host "2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "3. Navigate to this folder and run this script again" -ForegroundColor White
    Write-Host ""
    Write-Host "OR install Git manually from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Git is already installed
Write-Host "Checking for Git installation..." -ForegroundColor Yellow
try {
    $gitVersion = git --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Git is already installed: $gitVersion" -ForegroundColor Green
        $gitInstalled = $true
    } else {
        $gitInstalled = $false
    }
} catch {
    $gitInstalled = $false
}

if (-not $gitInstalled) {
    Write-Host "Git is not installed. Attempting to install..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1: Install via winget (if available)" -ForegroundColor Cyan
    Write-Host "Option 2: Download installer manually" -ForegroundColor Cyan
    Write-Host ""
    
    # Try winget first
    try {
        $wingetVersion = winget --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Found winget. Installing Git..." -ForegroundColor Yellow
            winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Git installed successfully!" -ForegroundColor Green
                Write-Host "Please close and reopen PowerShell for changes to take effect." -ForegroundColor Yellow
                Write-Host ""
                Write-Host "After restarting PowerShell, run the setup script again." -ForegroundColor Yellow
                Read-Host "Press Enter to exit"
                exit 0
            }
        }
    } catch {
        Write-Host "Winget not available." -ForegroundColor Yellow
    }
    
    # If winget failed, provide manual instructions
    Write-Host ""
    Write-Host "Please install Git manually:" -ForegroundColor Yellow
    Write-Host "1. Go to: https://git-scm.com/download/win" -ForegroundColor White
    Write-Host "2. Download and run the installer" -ForegroundColor White
    Write-Host "3. Use default settings during installation" -ForegroundColor White
    Write-Host "4. After installation, close and reopen PowerShell" -ForegroundColor White
    Write-Host "5. Run this script again to set up the repository" -ForegroundColor White
    Write-Host ""
    Write-Host "Opening download page in browser..." -ForegroundColor Yellow
    Start-Process "https://git-scm.com/download/win"
    Read-Host "Press Enter after installing Git to continue"
}

# Refresh PATH to ensure git is available
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Verify Git is now available
try {
    $gitVersion = git --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Git is still not available. Please restart PowerShell and try again." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "✓ Git is ready: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git is still not available. Please restart PowerShell and try again." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Now set up the repository
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setting up Local Git Repository" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$repoPath = "C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation"
Set-Location $repoPath

# Initialize git repository
Write-Host "Initializing git repository..." -ForegroundColor Yellow
if (Test-Path ".git") {
    Write-Host "⚠ Repository already exists. Reinitializing..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .git
}
git init
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to initialize repository!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Repository initialized" -ForegroundColor Green

# Create .gitignore
Write-Host ""
Write-Host "Creating .gitignore file..." -ForegroundColor Yellow
if (-not (Test-Path ".gitignore")) {
    @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
desktop.ini

# Logs
*.log

# Temporary files
*.tmp
*.temp
~$*

# Excel temporary files
~$*.xlsx
~$*.xls

# OneDrive
*.odtmp

# Sensitive data (if any)
*password*
*secret*
*key*
*.pem
*.key
"@ | Out-File -FilePath ".gitignore" -Encoding UTF8
    Write-Host "✓ .gitignore created" -ForegroundColor Green
} else {
    Write-Host "✓ .gitignore already exists" -ForegroundColor Green
}

# Add all files
Write-Host ""
Write-Host "Adding all files to repository..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to add files!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Files added" -ForegroundColor Green

# Create initial commit
Write-Host ""
Write-Host "Creating initial commit..." -ForegroundColor Yellow
git commit -m "Initial backup - Updated CCMD Software, 12/09/2025"
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ No changes to commit (or commit failed)" -ForegroundColor Yellow
} else {
    Write-Host "✓ Initial commit created" -ForegroundColor Green
}

# Set branch to main
Write-Host ""
Write-Host "Setting branch to main..." -ForegroundColor Yellow
git branch -M main 2>$null
Write-Host "✓ Branch set to main" -ForegroundColor Green

# Add remote
Write-Host ""
Write-Host "Adding GitHub remote..." -ForegroundColor Yellow
git remote remove origin 2>$null
git remote add origin https://github.com/mgthompson2001/In-Office-Installation.git
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Remote added" -ForegroundColor Green
} else {
    Write-Host "⚠ Failed to add remote" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Local Repository Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next step: Push to GitHub" -ForegroundColor Yellow
Write-Host ""
Write-Host "To push to GitHub, run:" -ForegroundColor White
Write-Host "  git push -u origin main" -ForegroundColor Cyan
Write-Host ""
Write-Host "You'll be prompted for your GitHub username and password/token." -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit"

