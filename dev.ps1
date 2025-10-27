# Development Helper Script
# This script sets up the environment for local development

$env:PYTHONPATH = "$PSScriptRoot\src"

Write-Host "✅ PYTHONPATH configured: $env:PYTHONPATH" -ForegroundColor Green
Write-Host ""
Write-Host "Available commands:" -ForegroundColor Cyan
Write-Host "  • uvicorn main:app --reload         (Run FastAPI server)" -ForegroundColor Yellow
Write-Host "  • python -m pytest tests/           (Run tests)" -ForegroundColor Yellow
Write-Host "  • ruff check src/                   (Check code quality)" -ForegroundColor Yellow
Write-Host "  • ruff format src/                  (Format code)" -ForegroundColor Yellow
Write-Host ""
Write-Host "To activate, run: . .\dev.ps1" -ForegroundColor Magenta
