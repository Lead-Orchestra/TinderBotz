#!/bin/bash
# Setup script for TinderBotz Python virtual environment using uv

set -e

echo "[*] Setting up TinderBotz Python virtual environment with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "[X] Error: uv is not installed"
    echo "[+] Please install uv first:"
    echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "    Or visit: https://github.com/astral-sh/uv"
    exit 1
fi

echo "[OK] uv is installed"

# Create virtual environment
echo "[*] Creating virtual environment..."
uv venv

# Activate virtual environment
echo "[*] Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "[*] Installing dependencies..."
uv pip install -e .

echo "[OK] Virtual environment setup complete!"
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the scraper:"
echo "  uv run python Scraper/tinder_profile_scraper.py ..."


