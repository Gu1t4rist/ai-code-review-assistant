#!/bin/bash
# Setup script for AI Code Review Assistant

set -e

echo "🚀 Setting up AI Code Review Assistant..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

echo "📌 Python version: $python_version"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Error: Python 3.10 or higher is required"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies
echo "📥 Installing development dependencies..."
pip install -e ".[dev]"

# Copy environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your GitLab and AI provider credentials"
echo "2. Run tests: pytest"
echo "3. Start webhook server: python -m ai_code_review.main webhook"
echo "4. Or review a specific MR: python -m ai_code_review.main review --project-id 123 --mr-iid 45"
echo ""
echo "For Docker deployment:"
echo "  docker-compose up -d"
echo ""
