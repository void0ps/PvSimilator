@echo off
echo ========================================
echo Stopping PV Simulator Docker Services
echo ========================================
echo.

docker-compose down

echo.
echo Services stopped successfully
pause
