@echo off
REM Startup script for AgentHub backend server (Windows)

echo Starting AgentHub Backend Server...
echo ====================================

REM Check if virtual environment exists
if not exist "venv\" (
    echo Error: Virtual environment not found!
    echo Please create it first: python -m venv venv
    exit /b 1
)

REM Check if Docker services are running
echo Checking Docker services...
docker ps | findstr "agenthub-postgres" >nul 2>&1
if errorlevel 1 (
    echo Starting Docker services...
    docker-compose up -d
    echo Waiting for PostgreSQL to be ready...
    timeout /t 5 /nobreak >nul
)

REM Set Python path
set PYTHONPATH=.

REM Start server
echo.
echo Starting FastAPI server on http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo Health Check: http://localhost:8000/health
echo.
echo Press Ctrl+C to stop the server
echo ====================================
echo.

venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > server.log 2>&1
