@echo off
setlocal
cd /d "%~dp0"

:: Check if python is in path
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found in PATH. Please install Python.
    pause
    exit /b 1
)

:: Close any existing pythonw instances of this bot
echo Stopping existing instances...
taskkill /IM pythonw.exe /F >nul 2>&1

:: Install dependencies
echo Installing/Updating dependencies...
pip install -r requirements.txt --quiet

:: Run the bot in the background using pythonw (no console window)
echo Starting WarEra Battle Checker in background...
start "" pythonw main.py

echo.
echo Bot started in background.
echo To stop it, use Task Manager to end the "pythonw.exe" process.
timeout /t 5
exit
