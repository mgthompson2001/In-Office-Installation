Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut(oWS.SpecialFolders("Desktop") & "\Automation Hub.lnk")
oLink.TargetPath = "C:\Users\MichaelLocal\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe"
oLink.Arguments = """C:\Users\MichaelLocal\Desktop\In-Office Installation\_system\secure_launcher.py"""
oLink.WorkingDirectory = "C:\Users\MichaelLocal\Desktop\In-Office Installation"
oLink.Description = "Automation Hub - Bot Launcher"
oLink.IconLocation = "C:\Users\MichaelLocal\Desktop\In-Office Installation\_system\ccmd_bot_icon.ico,0"
oLink.Save
WScript.Echo "Shortcut created successfully!"

