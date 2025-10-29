#!/bin/bash
# Startup script for AgentHub backend server

set -e  # Exit on error

echo "Starting AgentHub Backend Server..."
echo "===================================="

# Navigate to backend directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please create it first: python -m venv venv"
    exit 1
fi

# Check if Docker services are running
echo "Checking Docker services..."
if ! docker ps | grep -q "agenthub-postgres"; then
    echo "Starting Docker services..."
    docker-compose up -d
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
fi

# Set Python path
export PYTHONPATH=.

# Start server
echo ""
echo "Starting FastAPI server on http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo "===================================="

./venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
