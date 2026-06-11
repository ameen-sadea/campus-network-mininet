@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "FRONTEND=%CD%\frontend"

echo.
echo ========================================
echo   Campus Network Demo
echo ========================================
echo.
echo DIR: %CD%
echo.

where wsl >nul 2>&1
if errorlevel 1 (
    echo ERROR: WSL not found. Run: wsl --install
    goto DONE
)

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Add Python to PATH.
    goto DONE
)

if not exist "%FRONTEND%\index.html" (
    echo ERROR: Missing %FRONTEND%\index.html
    goto DONE
)

echo [1/4] WSL OK

echo [2/4] Starting Mininet API (WSL) + frontend HTTP server...
echo       sudo password may be required in MininetAPI window.
start "MininetAPI" cmd /k wsl --cd "%CD%" sudo bash -c "mn -c 2>/dev/null; exec python3 campus_network.py --api"
start "FrontendHTTP" cmd /k cd /d "%FRONTEND%" ^& python -m http.server 8000

echo [3/4] Waiting for API inside WSL (up to 120s)...
set /a WAIT=0
:wait_api
set /a WAIT+=1
if !WAIT! gtr 60 goto api_timeout

wsl python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/status', timeout=3)" >nul 2>&1
if not errorlevel 1 goto api_ready

set /a SEC=!WAIT!*2
echo       ... !SEC!s
timeout /t 2 /nobreak >nul
goto wait_api

:api_timeout
echo WARN: API not ready in 120s. Opening browser anyway.
goto open_browser

:api_ready
echo       API ready

:open_browser
echo [4/4] Opening browser...
set "WSL_IP="
for /f "tokens=1" %%i in ('wsl hostname -I 2^>nul') do set "WSL_IP=%%i"
if defined WSL_IP (
    echo       API: http://!WSL_IP!:5000
    start "" "http://localhost:8000/index.html?api=http://!WSL_IP!:5000"
) else (
    start "" "http://localhost:8000/index.html"
)

echo.
echo Done. Keep MininetAPI and FrontendHTTP windows open.
echo Close those windows to stop the demo.

:DONE
pause
