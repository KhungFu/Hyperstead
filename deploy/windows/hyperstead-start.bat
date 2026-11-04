@echo off
rem Hyperstead unter Windows starten (vorher einmal install.ps1 ausfuehren)
cd /d "%~dp0..\.."
venv\Scripts\python.exe app.py
pause
