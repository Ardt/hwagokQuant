#!/bin/bash
# Setup script for new machines

echo "🔧 Setting up hwagokQuant..."

# Git hooks
git config core.hooksPath .githooks
echo "✅ Git hooks configured"

# Python venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "✅ Python dependencies installed"

# Env file
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  Created .env from template — fill in your API keys"
else
  echo "✅ .env already exists"
fi

# Data directories
mkdir -p data/models
echo "✅ Data directories created"

echo ""
echo "🎉 Done! Next steps:"
echo "  1. Fill in .env with your API keys"
echo "  2. Set up ~/.oci/config for OCI Object Storage"
echo "  3. Run: python portfolio.py"
