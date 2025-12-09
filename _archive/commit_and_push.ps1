# Git Backup Script for In-Office Installation
# This script commits and pushes the current folder to GitHub

Write-Host "Starting git backup process..." -ForegroundColor Green

# Check if git is available
$gitPath = $null
$possiblePaths = @(
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files\Git\bin\git.exe",
    "C:\Program Files (x86)\Git\cmd\git.exe",
    "C:\Program Files (x86)\Git\bin\git.exe",
    "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe",
    "$env:LOCALAPPDATA\Programs\Git\bin\git.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $gitPath = $path
        $env:Path += ";$(Split-Path $path -Parent)"
        Write-Host "Found git at: $gitPath" -ForegroundColor Yellow
        break
    }
}

# Check GitHub Desktop git location
if (-not $gitPath) {
    $ghdPath = Get-ChildItem "$env:LOCALAPPDATA\GitHubDesktop" -Directory -Filter "app-*" -ErrorAction SilentlyContinue | 
               Sort-Object Name -Descending | 
               Select-Object -First 1
    
    if ($ghdPath) {
        $ghdGit = Join-Path $ghdPath.FullName "resources\app\git\cmd\git.exe"
        if (Test-Path $ghdGit) {
            $gitPath = $ghdGit
            $env:Path += ";$(Split-Path $ghdGit -Parent)"
            Write-Host "Found GitHub Desktop git at: $gitPath" -ForegroundColor Yellow
        }
    }
}

# Try using git command directly (if in PATH)
if (-not $gitPath) {
    try {
        $null = Get-Command git -ErrorAction Stop
        $gitPath = "git"
        Write-Host "Using git from PATH" -ForegroundColor Yellow
    } catch {
        Write-Host "ERROR: Git not found. Please install Git for Windows or ensure it's in your PATH." -ForegroundColor Red
        Write-Host "Download from: https://git-scm.com/download/win" -ForegroundColor Yellow
        exit 1
    }
}

# Function to run git commands
function Run-Git {
    param($Command)
    Write-Host "Running: git $Command" -ForegroundColor Cyan
    if ($gitPath -eq "git") {
        $result = & git $Command.Split(' ')
    } else {
        $result = & $gitPath $Command.Split(' ')
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Git command failed with exit code: $LASTEXITCODE" -ForegroundColor Red
        return $false
    }
    return $true
}

# Check current branch and status
Write-Host "`nChecking git status..." -ForegroundColor Green
if (-not (Run-Git "status")) {
    exit 1
}

# Create a new branch with timestamp
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$branchName = "backup-$timestamp"
Write-Host "`nCreating new branch: $branchName" -ForegroundColor Green

if (-not (Run-Git "checkout -b $branchName")) {
    Write-Host "Failed to create branch, trying to switch if it exists..." -ForegroundColor Yellow
    Run-Git "checkout $branchName"
}

# Add all changes
Write-Host "`nAdding all changes..." -ForegroundColor Green
if (-not (Run-Git "add -A")) {
    exit 1
}

# Commit changes
$commitMessage = "Backup: In-Office Installation folder - $timestamp"
Write-Host "`nCommitting changes..." -ForegroundColor Green
Write-Host "Commit message: $commitMessage" -ForegroundColor Cyan

if (-not (Run-Git "commit -m `"$commitMessage`"")) {
    Write-Host "`nNo changes to commit or commit failed." -ForegroundColor Yellow
    $hasChanges = $false
} else {
    $hasChanges = $true
}

# Check remote configuration
Write-Host "`nChecking remote configuration..." -ForegroundColor Green
$remoteUrl = ""
if ($gitPath -eq "git") {
    $remoteUrl = & git config --get remote.origin.url 2>$null
} else {
    $remoteUrl = & $gitPath config --get remote.origin.url 2>$null
}

if ($remoteUrl) {
    Write-Host "Remote URL: $remoteUrl" -ForegroundColor Cyan
    
    # Push to remote
    if ($hasChanges) {
        Write-Host "`nPushing to remote..." -ForegroundColor Green
        if (Run-Git "push -u origin $branchName") {
            Write-Host "`n✅ Successfully pushed to GitHub!" -ForegroundColor Green
            Write-Host "Branch: $branchName" -ForegroundColor Cyan
            Write-Host "Remote: $remoteUrl" -ForegroundColor Cyan
        } else {
            Write-Host "`n⚠️ Failed to push. You may need to authenticate or the remote may have changed." -ForegroundColor Yellow
            Write-Host "You can manually push using: git push -u origin $branchName" -ForegroundColor Yellow
        }
    } else {
        Write-Host "`nNo changes to push." -ForegroundColor Yellow
    }
} else {
    Write-Host "`n⚠️ No remote configured. Setting remote to GitHub..." -ForegroundColor Yellow
    if (Run-Git "remote add origin https://github.com/mgthompson2001/CCMD-Bot-Master.git") {
        Write-Host "Remote added. Pushing..." -ForegroundColor Green
        if ($hasChanges) {
            Run-Git "push -u origin $branchName"
        }
    }
}

Write-Host "`n✅ Backup process complete!" -ForegroundColor Green
