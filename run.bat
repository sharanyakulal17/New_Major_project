@echo off
title AURA-HEAL: Self-Healing Cloud Orchestrator & Analytics
color 0b

echo ======================================================================
echo          AURA-HEAL - Self-Healing Cloud Orchestrator & ML Engine
echo ======================================================================
echo.

:: Get directory of script
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Check for virtual environment
if exist "%SCRIPT_DIR%..\venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment...
    call "%SCRIPT_DIR%..\venv\Scripts\activate.bat"
) else if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment...
    call "%SCRIPT_DIR%venv\Scripts\activate.bat"
) else (
    echo [!] Using system Python...
)

:: Navigate to backend
if exist "%SCRIPT_DIR%backend\app.py" (
    cd /d "%SCRIPT_DIR%backend"
)

echo [*] Launching Self-Healing Backend Server on http://localhost:5001 ...
echo [*] Press Ctrl+C in this window to stop the server.
echo.

:: Automatically open browser after 2 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5001"

:: Start Flask server
python app.py

pause
