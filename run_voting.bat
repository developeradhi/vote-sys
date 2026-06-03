@echo off
cd /d "%~dp0"
echo ========================================================
echo GOVERNMENT ELECTORAL SYSTEM BOOTSTRAP (FLASK)
echo ========================================================

IF NOT EXIST "venv" (
    echo Creating Virtual Environment...
    python -m venv venv
)

echo Activating Virtual Environment...
call venv\Scripts\activate.bat

echo Installing dependencies (this is extremely fast if cached)...
pip install -r requirements.txt > nul 2>&1

echo Booting secure government portal...
echo.
echo ----------------------------------------------------
echo SYSTEM IS LIVE:
echo VOTER PORTAL: http://localhost:8501/voter/login
echo ADMIN PORTAL: http://localhost:8501/admin/login
echo ----------------------------------------------------
echo Press CTRL+C to safely shut down the server.
echo.

python app.py

pause
