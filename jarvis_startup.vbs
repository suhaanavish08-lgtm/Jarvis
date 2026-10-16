Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Jarvis\Jarvis"
WshShell.Run "cmd.exe /c "".\.venv\Scripts\python.exe"" src\main.py", 0, False
Set WshShell = Nothing
