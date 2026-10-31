@echo off
cd /d "%~dp0"

.venv\Scripts\python.exe backend/main.py
pause