#!/bin/bash

# Smart Research Paper Analyzer - Startup Script

echo "Starting Smart Research Paper Analyzer Backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Qdrant if not running
echo "Checking Qdrant..."
if ! docker ps | grep -q qdrant; then
    echo "Starting Qdrant..."
    docker-compose up -d qdrant
    echo "Waiting for Qdrant to be ready..."
    sleep 5
fi

# Start the FastAPI application
echo "Starting FastAPI application..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000

