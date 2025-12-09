Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the script directory (where this VBS file is located)
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Get desktop path (works on all Windows systems)
desktopPath = WshShell.SpecialFolders("Desktop")
shortcutPath = desktopPath & "\Automation Hub.lnk"

' Create shortcut
Set shortcut = WshShell.CreateShortcut(shortcutPath)
shortcut.TargetPath = scriptDir & "\launch_automation_hub.vbs"
shortcut.WorkingDirectory = scriptDir
shortcut.Description = "Automation Hub - Enterprise Bot Launcher"
shortcut.WindowStyle = 1 ' Minimized (no console window)

' Try to find icon (if available) - use absolute path
iconPath = scriptDir & "\ccmd_bot_icon.ico"
If Not fso.FileExists(iconPath) Then
    iconPath = scriptDir & "\automation_hub.ico"
End If
If fso.FileExists(iconPath) Then
    ' Get absolute path to ensure icon loads correctly
    Set iconFile = fso.GetFile(iconPath)
    absIconPath = iconFile.Path
    shortcut.IconLocation = absIconPath & ",0"
End If

shortcut.Save

' Success message
WScript.Echo "Desktop shortcut created: Automation Hub.lnk"

