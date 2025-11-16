# PV Simulator Docker Stop Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stopping PV Simulator Docker Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

docker-compose down

Write-Host ""
Write-Host "Services stopped successfully" -ForegroundColor Green
Read-Host "Press Enter to exit"
