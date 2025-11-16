@echo off
chcp 65001 >nul
echo ========================================
echo Starting PV Simulator Docker Services
echo ========================================
echo.

REM Check if Docker command exists
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not in PATH.
    echo.
    echo Please install Docker Desktop from:
    echo https://www.docker.com/products/docker-desktop
    echo.
    echo After installation, make sure Docker Desktop is running.
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    echo.
    echo Please start Docker Desktop and wait for it to be ready.
    echo You can check Docker status in the system tray.
    echo.
    pause
    exit /b 1
)

echo [1/3] Building Docker images...
docker-compose build

if errorlevel 1 (
    echo [ERROR] Build failed
    echo.
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo [2/3] Starting services...
docker-compose up -d

if errorlevel 1 (
    echo [ERROR] Failed to start services
    echo.
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo [3/3] Checking service status...
timeout /t 3 >nul
docker-compose ps

echo.
echo ========================================
echo Services started successfully!
echo ========================================
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo View logs:  docker-compose logs -f
echo Stop services: docker-compose down
echo ========================================
pause
