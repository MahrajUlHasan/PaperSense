#!/bin/bash
# Setup script for Smart Research Paper Analyzer Backend
# This script creates a virtual environment and installs all dependencies

echo "========================================"
echo "Smart Research Paper Analyzer - Setup"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

echo "[1/5] Checking Python version..."
python3 --version

echo ""
echo "[2/5] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Removing old one..."
    rm -rf venv
fi

python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    exit 1
fi

echo "Virtual environment created successfully!"

echo ""
echo "[3/5] Activating virtual environment..."
source venv/bin/activate

echo ""
echo "[4/5] Upgrading pip..."
pip install --upgrade pip

echo ""
echo "[5/5] Installing dependencies..."
echo "This may take a few minutes..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to install dependencies"
    echo "Please check the error messages above"
    exit 1
fi

echo ""
echo "========================================"
echo "Setup completed successfully!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and add your API keys"
echo "   cp .env.example .env"
echo ""
echo "2. Start Qdrant vector database:"
echo "   docker-compose up -d"
echo ""
echo "3. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "4. Run the backend server:"
echo "   python main.py"
echo "   or"
echo "   uvicorn main:app --reload"
echo ""
echo "========================================"

