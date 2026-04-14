# Run FastAPI Backend for WhatsApp Property Scrapper
# This script starts the backend API server on port 8000

Write-Host "🚀 Starting WhatsApp Property Lead Extractor Backend..." -ForegroundColor Green
Write-Host "Backend will run on http://localhost:8000" -ForegroundColor Cyan

# Check if virtual environment is activated
if (-not (Test-Path .venv)) {
    Write-Host "❌ Virtual environment not found. Run setup first." -ForegroundColor Red
    exit 1
}

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Run the backend
python -m uvicorn backend:app --reload --host 0.0.0.0 --port 8000
