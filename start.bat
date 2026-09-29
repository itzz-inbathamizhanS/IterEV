@echo off
setlocal enabledelayedexpansion

echo =======================================
echo IterEV Environment Check ^& Startup
echo =======================================
echo.

:: 1. Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Python is not installed or not in PATH.
    echo [INFO] Attempting to automatically install Python using Windows Package Manager (winget)...
    where winget >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] winget is not available on this laptop. Please install Python 3.9+ manually from python.org.
        pause
        exit /b
    )
    winget install --id Python.Python.3.11 --exact --silent --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install Python automatically. Please install manually.
        pause
        exit /b
    )
    echo [OK] Python installed successfully! 
    echo PLEASE RESTART THIS SCRIPT (or your terminal) so Windows can recognize the new Python PATH.
    pause
    exit /b
) else (
    echo [OK] Python is installed.
)

:: 2. Check Node.js
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Node.js (npm) is not installed or not in PATH.
    echo [INFO] Attempting to automatically install Node.js using Windows Package Manager (winget)...
    where winget >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] winget is not available on this laptop. Please install Node.js manually from nodejs.org.
        pause
        exit /b
    )
    winget install --id OpenJS.NodeJS.LTS --exact --silent --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install Node.js automatically. Please install manually.
        pause
        exit /b
    )
    echo [OK] Node.js installed successfully! 
    echo PLEASE RESTART THIS SCRIPT (or your terminal) so Windows can recognize the new Node.js PATH.
    pause
    exit /b
) else (
    echo [OK] Node.js and npm are installed.
)

:: 3. Setup Backend
echo.
echo Checking Backend Requirements...
cd Backend

if not exist venv\ (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)

echo [INFO] Verifying backend dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt
cd ..

:: 4. Setup Frontend
echo.
echo Checking Frontend Requirements...
cd Frontend

if not exist node_modules\ (
    echo [INFO] Installing frontend dependencies (this may take a minute)...
    call npm install
) else (
    echo [OK] Frontend node_modules exist.
)
cd ..

:: 5. Start Servers
echo.
echo =======================================
echo Starting IterEV Servers...
echo =======================================
echo.

echo Starting Backend...
start "IterEV Backend" cmd /k "cd Backend && call venv\Scripts\activate.bat && python -m uvicorn main:app --reload --port 8000"

echo Starting Frontend...
start "IterEV Frontend" cmd /k "cd Frontend && npm run dev"

echo.
echo Both servers are starting in separate windows.
echo - Backend will be available at: http://localhost:8000
echo - Frontend will be available at: http://localhost:8080
echo.
echo You can close this window now.
pause
