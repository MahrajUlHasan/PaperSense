@echo off
REM Setup script for Smart Research Paper Analyzer Backend
REM This script creates a virtual environment and installs all dependencies

echo ========================================
echo Smart Research Paper Analyzer - Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

echo.
echo [2/5] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists. Removing old one...
    rmdir /s /q venv
)

python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Virtual environment created successfully!

echo.
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [4/5] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [5/5] Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    echo Please check the error messages above
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Copy .env.example to .env and add your API keys
echo    copy .env.example .env
echo.
echo 2. Start Qdrant vector database:
echo    docker-compose up -d
echo.
echo 3. Activate the virtual environment:
echo    venv\Scripts\activate
echo.
echo 4. Run the backend server:
echo    python main.py
echo    or
echo    uvicorn main:app --reload
echo.
echo ========================================
pause

