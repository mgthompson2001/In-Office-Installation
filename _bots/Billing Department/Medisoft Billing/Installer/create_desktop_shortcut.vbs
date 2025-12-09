' Medisoft Billing Bot - Desktop Shortcut Creator
' Creates a desktop shortcut with red I icon
' Usage: cscript create_desktop_shortcut.vbs "InstallDir" "TargetBat"

Set objArgs = WScript.Arguments
If objArgs.Count < 2 Then
    WScript.Echo "Usage: create_desktop_shortcut.vbs InstallDir TargetBat"
    WScript.Quit 1
End If

InstallDir = objArgs(0)
TargetBat = objArgs(1)

' Get desktop path
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

DesktopPath = objShell.SpecialFolders("Desktop")
ShortcutPath = DesktopPath & "\Medisoft Billing Bot.lnk"

' Create shortcut
Set objShortcut = objShell.CreateShortcut(ShortcutPath)
objShortcut.TargetPath = TargetBat
objShortcut.WorkingDirectory = InstallDir
objShortcut.Description = "Launch Medisoft Billing Bot"
objShortcut.IconLocation = InstallDir & "\Installer\medisoft_bot_icon.ico"

' Try to find or create icon (check multiple locations and formats)
IconPath = InstallDir & "\Installer\medisoft_bot_icon.ico"
If Not objFSO.FileExists(IconPath) Then
    IconPath = InstallDir & "\Installer\medisoft_bot_icon.png"
    If Not objFSO.FileExists(IconPath) Then
        IconPath = InstallDir & "\Installer\icon.ico"
        If Not objFSO.FileExists(IconPath) Then
            ' Try parent directories for shared icon
            IconPath = InstallDir & "\..\..\..\_admin\ccmd_bot_icon.png"
            If Not objFSO.FileExists(IconPath) Then
                IconPath = InstallDir & "\medisoft_billing_bot.ico"
                If Not objFSO.FileExists(IconPath) Then
                    ' Use default Python icon as fallback
                    On Error Resume Next
                    IconPath = objShell.RegRead("HKEY_LOCAL_MACHINE\SOFTWARE\Python\PythonCore\3.11\InstallPath\")
                    If Err.Number <> 0 Then
                        IconPath = objShell.RegRead("HKEY_LOCAL_MACHINE\SOFTWARE\Python\PythonCore\3.10\InstallPath\")
                    End If
                    On Error Goto 0
                    If Not IsEmpty(IconPath) And objFSO.FileExists(IconPath & "\python.exe") Then
                        IconPath = IconPath & "\python.exe,0"
                    Else
                        ' Last resort: use system icon
                        IconPath = "%SystemRoot%\System32\shell32.dll,1"
                    End If
                End If
            End If
        End If
    End If
End If

objShortcut.IconLocation = IconPath
objShortcut.Save

WScript.Echo "Desktop shortcut created successfully at: " & ShortcutPath
WScript.Echo "Icon location: " & IconPath

