@echo off
cd /d "%~dp0"

start "FastAPI Backend" cmd /k ".venv\Scripts\python.exe backend/main.py"
start "Vite Frontend" cmd /k "npm --prefix frontend run dev"