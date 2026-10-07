@echo off
chcp 65001 >nul
title VoiceStudio_CF Launcher
cd /d "%~dp0"

set "PYTHON_EXE=python.exe"
set "PYTHONW_EXE=pythonw.exe"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
    set "PYTHONW_EXE=%CD%\.venv\Scripts\pythonw.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    set "PYTHONW_EXE=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
)

echo [VoiceStudio_CF] Đang khởi động ứng dụng VoiceStudio_CF...
start "" /b "%PYTHONW_EXE%" -m voicestudio_cf.app.main
if %ERRORLEVEL% NEQ 0 (
    echo [VoiceStudio_CF] Thử khởi động bằng Python console: %PYTHON_EXE%
    "%PYTHON_EXE%" -m voicestudio_cf.app.main
)
exit /b 0
