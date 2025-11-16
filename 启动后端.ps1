# PV Simulator Backend Launcher
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  PV Simulator - Backend Service" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to backend directory
Set-Location -Path "$PSScriptRoot\backend"
Write-Host "[1/2] Working directory: $PWD" -ForegroundColor Yellow
Write-Host "      (使用系统Python环境)" -ForegroundColor Gray

# Start backend
Write-Host "[2/2] Starting backend service..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Backend will be available at:" -ForegroundColor Green
Write-Host "  - API: http://localhost:8000" -ForegroundColor White
Write-Host "  - Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python main.py

