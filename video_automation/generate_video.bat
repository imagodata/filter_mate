@echo off
REM ================================================================
REM FilterMate Video Generator - One-click video production
REM Generates: 12 diagrams (HTML→PNG) + TTS narration + final MP4
REM ================================================================

echo.
echo ============================================
echo  FilterMate Video Generator
echo  Diagrams + Narration = Video
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

REM Check/install FFmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] FFmpeg not found. Install from https://ffmpeg.org/download.html
    echo          Or: winget install ffmpeg
    echo          Video assembly will be skipped.
)

REM Install dependencies
echo [1/5] Installing Python dependencies...
pip install edge-tts Pillow pyyaml playwright --quiet 2>nul
python -m playwright install chromium --quiet 2>nul

REM Generate diagrams
echo [2/5] Generating diagrams...
cd /d "%~dp0"
python generate_diagrams_standalone.py

REM Generate narration
echo [3/5] Generating TTS narration...
python generate_narration_standalone.py

REM Assemble video
echo [4/5] Assembling video...
ffmpeg -version >nul 2>&1
if %errorlevel% equ 0 (
    python assemble_video_standalone.py
) else (
    echo [SKIP] FFmpeg not available, skipping video assembly.
    echo        Install FFmpeg and re-run, or assemble manually.
)

echo.
echo [5/5] Done!
echo.
echo Output files in: %~dp0output\
echo   diagrams\  - 12 PNG diagrams (1920x1080)
echo   narration\ - 11 MP3 narration files
echo   final\     - Final MP4 video
echo.
pause
