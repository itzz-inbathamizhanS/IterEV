@echo off
echo Starting IterEV...

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
