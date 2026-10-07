@echo off
chcp 65001 >nul
title Setup Environment - VoiceStudio_CF
cd /d "%~dp0"

echo =======================================================
echo          VoiceStudio_CF - Cài đặt môi trường
echo =======================================================
echo.

where uv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [1/3] Phát hiện thấy công cụ UV siêu tốc.
    echo [2/3] Đang tạo môi trường ảo Python và cài đặt PyTorch CUDA...
    uv venv --python 3.12 .venv 2>nul
    if not exist ".venv\Scripts\python.exe" (
        uv venv .venv
    )
    echo [3/3] Đang đồng bộ thư viện và phụ thuộc...
    uv pip install --index-url https://download.pytorch.org/whl/cu128 torch torchaudio
    uv pip install -e .
    echo.
    echo Cài đặt hoàn tất! Bạn có thể chạy ứng dụng bằng run.bat
    pause
    exit /b 0
)

echo [1/3] UV không có sẵn, dùng pip tiêu chuẩn...
python -m venv .venv
call .venv\Scripts\activate.bat
echo [2/3] Cài đặt PyTorch với hỗ trợ CUDA...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
echo [3/3] Cài đặt các gói phụ thuộc còn lại...
pip install -e .
echo.
echo Cài đặt hoàn tất! Bạn có thể chạy ứng dụng bằng run.bat
pause
