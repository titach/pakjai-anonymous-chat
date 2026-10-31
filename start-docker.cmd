@echo off
setlocal EnableExtensions
cd /d "%~dp0"

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker Desktop is not ready. Open Docker Desktop and try again.
    pause
    exit /b 1
)
if not exist ".env" (
    echo Missing .env in the project root. Add API_KEY and SERVICE_URL first.
    pause
    exit /b 1
)

echo Building and starting Pakjai...
docker compose up --build -d --wait --wait-timeout 120
if errorlevel 1 goto failed

echo Waiting for the public link...
set "TUNNEL_URL="
for /l %%I in (1,1,45) do (
    for /f "tokens=4" %%U in ('docker compose logs --no-color --no-log-prefix tunnel 2^>nul ^| findstr /r /c:"https://[a-z0-9-]*\.trycloudflare\.com"') do set "TUNNEL_URL=%%U"
    if defined TUNNEL_URL goto ready
    ping -n 3 127.0.0.1 >nul
)
echo No public link yet. The local site is available at http://localhost:8080
echo Inspect tunnel status with: docker compose logs --tail 30 tunnel
pause
exit /b 1

:ready
echo.
echo ============================================================
echo Public link: %TUNNEL_URL%
echo Local site:  http://localhost:8080
echo ============================================================
echo All services run in Docker. You can close this window.
echo To stop everything, run stop-docker.cmd
pause
exit /b 0

:failed
echo Startup failed. Containers may still be running.
echo Check: docker compose ps
echo Check: docker compose logs --tail 30
echo Stop:  stop-docker.cmd
pause
exit /b 1
