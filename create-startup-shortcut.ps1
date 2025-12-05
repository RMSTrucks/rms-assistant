$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\RMS-Agent-Server.lnk")
$Shortcut.TargetPath = "C:\Users\Jake\WorkProjects\rms-assistant-extension\start-server.bat"
$Shortcut.WorkingDirectory = "C:\Users\Jake\WorkProjects\rms-assistant-extension\agent"
$Shortcut.WindowStyle = 7
$Shortcut.Save()
Write-Host "Startup shortcut created!"
