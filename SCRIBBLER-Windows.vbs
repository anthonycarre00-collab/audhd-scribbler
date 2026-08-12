Option Explicit
Dim shell, root, pythonw, script
Set shell = CreateObject("WScript.Shell")
root = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
pythonw = root & "\.venv\Scripts\pythonw.exe"
script = root & "\ScribblerWindows.py"
If Not CreateObject("Scripting.FileSystemObject").FileExists(pythonw) Then
  MsgBox "Scribbler is not installed yet. Please run INSTALL-Windows.bat first.", 48, "The Audhd Scribbler"
  WScript.Quit 1
End If
shell.Run Chr(34) & pythonw & Chr(34) & " " & Chr(34) & script & Chr(34), 0, False
