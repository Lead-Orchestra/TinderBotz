# Setup script for TinderBotz Python virtual environment using uv (Windows)

Write-Host "[*] Setting up TinderBotz Python virtual environment with uv..." -ForegroundColor Cyan

# Check if uv is installed
try {
    $null = Get-Command uv -ErrorAction Stop
    Write-Host "[OK] uv is installed" -ForegroundColor Green
} catch {
    Write-Host "[X] Error: uv is not installed" -ForegroundColor Red
    Write-Host "[+] Please install uv first:" -ForegroundColor Yellow
    Write-Host "    powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
    Write-Host "    Or visit: https://github.com/astral-sh/uv"
    exit 1
}

# Create virtual environment
Write-Host "[*] Creating virtual environment..." -ForegroundColor Cyan
uv venv

# Activate virtual environment
Write-Host "[*] Activating virtual environment..." -ForegroundColor Cyan
& .venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "[*] Installing dependencies..." -ForegroundColor Cyan
uv pip install -e .

Write-Host "[OK] Virtual environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the virtual environment:"
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "To run the scraper:"
Write-Host "  uv run python Scraper/tinder_profile_scraper.py ..."


