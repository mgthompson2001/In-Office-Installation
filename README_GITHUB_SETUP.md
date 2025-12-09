# GitHub Backup Setup Instructions

This folder will be backed up to GitHub repository: **Updated CCMD Software, 12/09/2025**

## Quick Setup

1. **Install Git** (if not already installed):
   - Download from: https://git-scm.com/download/win
   - Or install GitHub Desktop: https://desktop.github.com/

2. **Run the setup script**:
   - Double-click `setup_github_backup.ps1`
   - Or run in PowerShell: `.\setup_github_backup.ps1`

3. **Create GitHub Repository**:
   - Go to: https://github.com/new
   - Repository name: `Updated-CCMD-Software-12-09-2025`
   - Make it **PRIVATE** (recommended)
   - **DO NOT** initialize with README, .gitignore, or license

4. **Follow the script prompts** to connect and push to GitHub

## Manual Setup (Alternative)

If you prefer to set it up manually:

```bash
# Navigate to this folder
cd "C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation"

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial backup - Updated CCMD Software, 12/09/2025"

# Add remote (after creating repository on GitHub)
git remote add origin https://github.com/mgthompson2001/Updated-CCMD-Software-12-09-2025.git

# Rename branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

## GitHub Authentication

GitHub no longer accepts passwords for git operations. You'll need:

1. **Personal Access Token (PAT)**:
   - Go to: https://github.com/settings/tokens
   - Generate new token (classic)
   - Select scopes: `repo` (full control of private repositories)
   - Use the token as your password when pushing

2. **Or use GitHub Desktop** (easier for beginners)

## Repository Details

- **GitHub Username**: mgthompson2001
- **Repository Name**: Updated-CCMD-Software-12-09-2025
- **Date**: December 9, 2025

## Notes

- The `.gitignore` file will exclude temporary files, cache, and sensitive data
- Make sure to review what's being committed before pushing
- Consider making the repository private for security

