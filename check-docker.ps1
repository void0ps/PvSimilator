# Docker Health Check Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Docker Health Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker command
Write-Host "[1/4] Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "  Docker: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host "  Please install Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# Check Docker Compose
Write-Host "[2/4] Checking Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker-compose --version
    Write-Host "  Docker Compose: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "  [WARNING] docker-compose command not found" -ForegroundColor Yellow
    Write-Host "  Trying 'docker compose' (v2)..." -ForegroundColor Yellow
    try {
        $composeVersion = docker compose version
        Write-Host "  Docker Compose: $composeVersion" -ForegroundColor Green
    } catch {
        Write-Host "  [ERROR] Docker Compose not found" -ForegroundColor Red
        exit 1
    }
}

# Check Docker daemon
Write-Host "[3/4] Checking Docker daemon..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "  Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Docker daemon is not running" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Please:" -ForegroundColor Yellow
    Write-Host "  1. Start Docker Desktop" -ForegroundColor Yellow
    Write-Host "  2. Wait for it to fully initialize" -ForegroundColor Yellow
    Write-Host "  3. Check the system tray icon" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Check running containers
Write-Host "[4/4] Checking containers..." -ForegroundColor Yellow
try {
    $containers = docker ps --format "{{.Names}}"
    if ($containers) {
        Write-Host "  Running containers:" -ForegroundColor Green
        $containers | ForEach-Object { Write-Host "    - $_" -ForegroundColor Cyan }
    } else {
        Write-Host "  No containers running" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARNING] Could not list containers" -ForegroundColor Yellow
    Write-Host "  Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Docker is ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run:" -ForegroundColor Cyan
Write-Host "  .\docker-start.bat" -ForegroundColor Yellow
Write-Host "  or" -ForegroundColor Yellow
Write-Host "  .\docker-start.ps1" -ForegroundColor Yellow
Write-Host ""


