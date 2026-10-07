@echo off
cd /d "%~dp0"

set "PYTHONW_EXE=pythonw.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PYTHONW_EXE=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if exist ".venv\Scripts\pythonw.exe" set "PYTHONW_EXE=%CD%\.venv\Scripts\pythonw.exe"

start "" /b "%PYTHONW_EXE%" -m voicestudio_cf.app.main
exit /b 0
