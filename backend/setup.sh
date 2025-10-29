#!/bin/bash
# Quick setup script for AgentHub backend

set -e

echo "🚀 AgentHub Backend Setup"
echo "=========================="
echo ""

# Check Python version
echo "1. Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   Python version: $python_version"

if [[ $python_version < "3.11" ]]; then
    echo "   ⚠️  Python 3.11+ required"
    exit 1
fi
echo "   ✅ Python version OK"
echo ""

# Create virtual environment
echo "2. Creating virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "   ✅ Virtual environment created"
else
    echo "   ℹ️  Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "3. Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate
echo "   ✅ Virtual environment activated"
echo ""

# Install dependencies
echo "4. Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "   ✅ Dependencies installed"
echo ""

# Check .env file
echo "5. Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "   ⚠️  .env file not found"
    echo "   Creating .env from .env.example..."
    cp .env.example .env
    echo "   ⚠️  IMPORTANT: Edit .env and configure:"
    echo "      - DATABASE_URL"
    echo "      - JWT_PUBLIC_KEY"
    echo "      - FERNET_KEY (generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
else
    echo "   ✅ .env file exists"
fi
echo ""

# Start Docker services
echo "6. Starting Docker services..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
    echo "   ✅ Docker services starting (PostgreSQL, Redis, ChromaDB)"
    echo "   Waiting for services to be ready..."
    sleep 5
else
    echo "   ⚠️  docker-compose not found - please start services manually"
fi
echo ""

# Run migrations
echo "7. Running database migrations..."
alembic upgrade head
echo "   ✅ Database schema created"
echo ""

# Verify setup
echo "8. Verifying setup..."
python -c "from src.config import settings; print(f'   Database: {settings.DATABASE_URL}')"
echo "   ✅ Configuration loaded"
echo ""

echo "=========================="
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Start the API server: python src/main.py"
echo "3. Access API docs: http://localhost:8000/docs"
echo ""
echo "For more information, see README.md"
