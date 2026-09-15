@echo off
chcp 65001 > nul
cd /d "%~dp0"
python gemini_test.py
echo.
pause
