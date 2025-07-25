#!/bin/bash
# Setup script for DeFi Wallet Risk Scoring System

echo "🏦 Setting up DeFi Wallet Risk Scoring System..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.8+ first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To run the system:"
echo "  source .venv/bin/activate"
echo "  python score_wallets_improved.py"
echo ""
echo "Or with options:"
echo "  python score_wallets_improved.py --simulation"
echo "  python score_wallets_improved.py --workers 10"
echo "  python score_wallets_improved.py --quiet"
