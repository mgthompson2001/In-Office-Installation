# Diagnostic script to read desktop shortcut information
$shortcutPath = "C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\Automation Hub (2).lnk"

if (Test-Path $shortcutPath) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    
    Write-Host "=== Desktop Shortcut Analysis ===" -ForegroundColor Cyan
    Write-Host "Target Path: $($shortcut.TargetPath)" -ForegroundColor Yellow
    Write-Host "Arguments: $($shortcut.Arguments)" -ForegroundColor Yellow
    Write-Host "Working Directory: $($shortcut.WorkingDirectory)" -ForegroundColor Yellow
    Write-Host "Icon Location: $($shortcut.IconLocation)" -ForegroundColor Yellow
    Write-Host "Description: $($shortcut.Description)" -ForegroundColor Yellow
} else {
    Write-Host "Shortcut not found at: $shortcutPath" -ForegroundColor Red
}

