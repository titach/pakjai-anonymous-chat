@echo off
setlocal
cd /d "%~dp0"
docker compose down
if errorlevel 1 (
    echo Could not stop the stack. Check that Docker Desktop is running.
    pause
    exit /b 1
)
echo Pakjai stopped. The public link is now offline.
echo Rooms and messages were cleared when the backend stopped.
pause
