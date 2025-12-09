# Simple script to set up local git repository
# Run this AFTER Git is installed

Write-Host "Setting up local Git repository..." -ForegroundColor Cyan
Write-Host ""

$repoPath = "C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation"
Set-Location $repoPath

# Check if git is available
try {
    $null = git --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Git is not installed or not in PATH!" -ForegroundColor Red
        Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor Yellow
        Write-Host "Or run INSTALL_GIT_AND_SETUP.ps1 as Administrator" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
} catch {
    Write-Host "✗ Git is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Git is available" -ForegroundColor Green
Write-Host ""

# Initialize repository
Write-Host "Initializing git repository..." -ForegroundColor Yellow
if (Test-Path ".git") {
    Write-Host "⚠ Repository already exists" -ForegroundColor Yellow
    $response = Read-Host "Reinitialize? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        Remove-Item -Recurse -Force .git
        git init
    }
} else {
    git init
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to initialize!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Repository initialized" -ForegroundColor Green

# Create .gitignore
Write-Host ""
Write-Host "Creating .gitignore..." -ForegroundColor Yellow
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

# Sensitive data
*password*
*secret*
*key*
*.pem
*.key
"@ | Out-File -FilePath ".gitignore" -Encoding UTF8
    Write-Host "✓ .gitignore created" -ForegroundColor Green
}

# Add files
Write-Host ""
Write-Host "Adding all files..." -ForegroundColor Yellow
git add .
Write-Host "✓ Files added" -ForegroundColor Green

# Commit
Write-Host ""
Write-Host "Creating commit..." -ForegroundColor Yellow
git commit -m "Initial backup - Updated CCMD Software, 12/09/2025"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Commit created" -ForegroundColor Green
} else {
    Write-Host "⚠ No changes to commit" -ForegroundColor Yellow
}

# Set branch
Write-Host ""
Write-Host "Setting branch to main..." -ForegroundColor Yellow
git branch -M main 2>$null
Write-Host "✓ Branch set to main" -ForegroundColor Green

# Add remote
Write-Host ""
Write-Host "Adding GitHub remote..." -ForegroundColor Yellow
git remote remove origin 2>$null
git remote add origin https://github.com/mgthompson2001/In-Office-Installation.git
Write-Host "✓ Remote added" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Local repository is ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To push to GitHub, run:" -ForegroundColor Yellow
Write-Host "  git push -u origin main" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"

