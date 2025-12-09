# PowerShell script to backup folder to GitHub
# Repository: Updated CCMD Software, 12/09/2025
# GitHub Username: mgthompson2001

$repoName = "Updated-CCMD-Software-12-09-2025"
$githubUsername = "mgthompson2001"
$folderPath = "C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub Backup Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
Write-Host "Checking for Git installation..." -ForegroundColor Yellow
try {
    $gitVersion = git --version
    Write-Host "✓ Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "Or install GitHub Desktop from: https://desktop.github.com/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installing Git, run this script again." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Navigate to folder
Write-Host ""
Write-Host "Navigating to folder: $folderPath" -ForegroundColor Yellow
Set-Location $folderPath

# Check if already a git repository
if (Test-Path ".git") {
    Write-Host "⚠ Warning: This folder is already a git repository!" -ForegroundColor Yellow
    $response = Read-Host "Do you want to continue? (y/n)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Aborted." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Initializing git repository..." -ForegroundColor Yellow
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to initialize git repository!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Git repository initialized" -ForegroundColor Green
}

# Create .gitignore if it doesn't exist
if (-not (Test-Path ".gitignore")) {
    Write-Host ""
    Write-Host "Creating .gitignore file..." -ForegroundColor Yellow
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
}

# Add all files
Write-Host ""
Write-Host "Adding all files to git..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to add files!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Files added" -ForegroundColor Green

# Create initial commit
Write-Host ""
Write-Host "Creating initial commit..." -ForegroundColor Yellow
$commitMessage = "Initial backup - Updated CCMD Software, 12/09/2025"
git commit -m $commitMessage
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ No changes to commit (or commit failed)" -ForegroundColor Yellow
} else {
    Write-Host "✓ Initial commit created" -ForegroundColor Green
}

# Instructions for creating GitHub repository
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Go to GitHub and create a new repository:" -ForegroundColor Yellow
Write-Host "   https://github.com/new" -ForegroundColor White
Write-Host ""
Write-Host "2. Repository name: $repoName" -ForegroundColor Yellow
Write-Host "   (or use: Updated CCMD Software, 12/09/2025)" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Make it PRIVATE (recommended for software backups)" -ForegroundColor Yellow
Write-Host ""
Write-Host "4. DO NOT initialize with README, .gitignore, or license" -ForegroundColor Yellow
Write-Host ""
Write-Host "5. After creating the repository, run these commands:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   git remote add origin https://github.com/$githubUsername/$repoName.git" -ForegroundColor White
Write-Host "   git branch -M main" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Ask if user wants to set up remote now
$setupRemote = Read-Host "Have you created the GitHub repository? (y/n)"
if ($setupRemote -eq "y" -or $setupRemote -eq "Y") {
    Write-Host ""
    Write-Host "Setting up remote..." -ForegroundColor Yellow
    
    # Remove existing origin if it exists
    git remote remove origin 2>$null
    
    # Add new remote
    $remoteUrl = "https://github.com/$githubUsername/$repoName.git"
    git remote add origin $remoteUrl
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to add remote!" -ForegroundColor Red
        Write-Host "Please check the repository name and try again." -ForegroundColor Yellow
    } else {
        Write-Host "✓ Remote added: $remoteUrl" -ForegroundColor Green
        
        # Rename branch to main
        git branch -M main 2>$null
        
        # Push to GitHub
        Write-Host ""
        Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
        Write-Host "You may be prompted for your GitHub username and password/token." -ForegroundColor Yellow
        Write-Host ""
        
        git push -u origin main
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✓ Successfully pushed to GitHub!" -ForegroundColor Green
            Write-Host "Repository URL: https://github.com/$githubUsername/$repoName" -ForegroundColor Cyan
        } else {
            Write-Host ""
            Write-Host "⚠ Push failed. You may need to:" -ForegroundColor Yellow
            Write-Host "   - Use a Personal Access Token instead of password" -ForegroundColor Yellow
            Write-Host "   - Set up SSH keys" -ForegroundColor Yellow
            Write-Host "   - Check your GitHub credentials" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "You can try pushing manually with:" -ForegroundColor Yellow
            Write-Host "   git push -u origin main" -ForegroundColor White
        }
    }
} else {
    Write-Host ""
    Write-Host "When you're ready, run these commands:" -ForegroundColor Yellow
    Write-Host "   git remote add origin https://github.com/$githubUsername/$repoName.git" -ForegroundColor White
    Write-Host "   git branch -M main" -ForegroundColor White
    Write-Host "   git push -u origin main" -ForegroundColor White
}

Write-Host ""
Write-Host "Script completed!" -ForegroundColor Green
Read-Host "Press Enter to exit"

