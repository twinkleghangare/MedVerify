@echo off
echo ============================================
echo   MedVerify Backend - Setup and Start
echo ============================================
echo.

cd /d "%~dp0backend"

if not exist "venv" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/3] Virtual environment already exists, skipping.
)

echo [2/3] Installing dependencies (this can take a few minutes first time)...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo [3/3] Starting server at http://localhost:8000 ...
echo.
echo Leave this window open while using MedVerify.
echo Press CTRL+C to stop the server.
echo.
uvicorn app.main:app --reload --port 8000

pause
