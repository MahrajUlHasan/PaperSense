@echo off
REM Smart Research Paper Analyzer - Windows Startup Script

echo Starting Smart Research Paper Analyzer Backend...

REM Check if .env exists
if not exist .env (
    echo Error: .env file not found!
    echo Please copy .env.example to .env and configure your API keys
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Start Qdrant if not running
echo Checking Qdrant...
docker ps | findstr qdrant >nul
if errorlevel 1 (
    echo Starting Qdrant...
    docker-compose up -d qdrant
    echo Waiting for Qdrant to be ready...
    timeout /t 5 /nobreak >nul
)

REM Start the FastAPI application
echo Starting FastAPI application...
uvicorn main:app --reload --host 0.0.0.0 --port 8000

