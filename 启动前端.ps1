# PV Simulator Frontend Launcher
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  PV Simulator - Frontend Service" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to frontend directory
Set-Location -Path "$PSScriptRoot\frontend\analysis"
Write-Host "[1/2] Working directory: $PWD" -ForegroundColor Yellow

# Start frontend
Write-Host "[2/2] Starting frontend development server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Frontend will be available at:" -ForegroundColor Green
Write-Host "  - App: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

npm run dev

