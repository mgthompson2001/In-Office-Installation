Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the script directory
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcherScript = scriptDir & "\secure_launcher.py"

' Use pythonw.exe (no console window) - will use system path if available
' The 0 flag hides the window completely
WshShell.Run "pythonw.exe """ & launcherScript & """", 0, False

