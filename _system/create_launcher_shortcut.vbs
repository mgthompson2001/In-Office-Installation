Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the script directory
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Create shortcut on desktop
desktopPath = WshShell.SpecialFolders("Desktop")
shortcutPath = desktopPath & "\Automation Hub.lnk"

Set shortcut = WshShell.CreateShortcut(shortcutPath)
shortcut.TargetPath = scriptDir & "\launch_automation_hub.vbs"
shortcut.WorkingDirectory = scriptDir
shortcut.Description = "Automation Hub - Enterprise Bot Launcher"
shortcut.WindowStyle = 1 ' Minimized (no console window)

' Try to find icon (if available)
iconPath = scriptDir & "\automation_hub.ico"
If fso.FileExists(iconPath) Then
    shortcut.IconLocation = iconPath & ",0"
End If

shortcut.Save

WScript.Echo "Shortcut created on desktop: Automation Hub.lnk"

