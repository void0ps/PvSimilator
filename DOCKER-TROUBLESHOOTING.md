# Docker Troubleshooting Guide

## Issue: API Version Error (500 Internal Server Error)

If you see errors like:
```
request returned 500 Internal Server Error for API route and version
check if the server supports the requested API version
```

This usually indicates Docker Desktop is not fully started or needs to be restarted.

## Solutions

### Solution 1: Restart Docker Desktop (Most Common Fix)

1. **Right-click** the Docker icon in the system tray
2. Select **"Quit Docker Desktop"**
3. Wait a few seconds
4. **Start Docker Desktop** again from the Start menu
5. Wait for Docker to fully start (icon should be steady, not animating)
6. Try your command again

### Solution 2: Restart WSL2 (If Using WSL2 Backend)

1. Open PowerShell as Administrator
2. Run:
   ```powershell
   wsl --shutdown
   ```
3. Wait 10 seconds
4. Start Docker Desktop again
5. Wait for it to fully initialize

### Solution 3: Reset Docker Desktop

If the above doesn't work:

1. Open Docker Desktop
2. Go to **Settings** (gear icon)
3. Go to **Troubleshoot**
4. Click **"Reset to factory defaults"** (this will remove all containers and images)
5. Restart Docker Desktop

### Solution 4: Check Docker Desktop Resources

1. Open Docker Desktop
2. Go to **Settings** > **Resources**
3. Ensure:
   - **Memory**: At least 4GB allocated
   - **CPUs**: At least 2 CPUs allocated
   - **Disk image size**: Sufficient space (at least 20GB free)

### Solution 5: Update Docker Desktop

1. Open Docker Desktop
2. Go to **Settings** > **General**
3. Check for updates
4. Or download the latest version from: https://www.docker.com/products/docker-desktop

### Solution 6: Check Windows Features

Ensure these Windows features are enabled:
1. Open **Control Panel** > **Programs** > **Turn Windows features on or off**
2. Ensure these are checked:
   - **Virtual Machine Platform**
   - **Windows Subsystem for Linux** (if using WSL2)
   - **Hyper-V** (if using Hyper-V backend)

## Verify Docker is Working

After applying a solution, verify Docker is working:

```powershell
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version

# Test Docker (should work without errors)
docker ps

# Test Docker Compose
docker-compose version
```

## Common Issues

### Issue: "Docker daemon is not running"

**Fix**: Start Docker Desktop and wait for it to fully initialize.

### Issue: "Cannot connect to Docker daemon"

**Fix**: 
1. Restart Docker Desktop
2. Check if Docker Desktop is running in the system tray
3. Try running PowerShell/CMD as Administrator

### Issue: Port already in use

**Fix**: 
1. Find what's using the port:
   ```powershell
   netstat -ano | findstr :8000
   ```
2. Stop the process or change the port in `docker-compose.yml`

### Issue: Build fails with "no space left on device"

**Fix**:
1. Clean up Docker:
   ```powershell
   docker system prune -a
   ```
2. Increase Docker Desktop disk image size in Settings > Resources

## Still Having Issues?

1. Check Docker Desktop logs:
   - Open Docker Desktop
   - Go to Settings > Troubleshoot
   - Click "View logs"

2. Check Windows Event Viewer for Docker-related errors

3. Try running Docker commands in a new terminal window

4. Ensure Windows is up to date

5. Check if antivirus/firewall is blocking Docker

## Quick Health Check Script

Run this to check Docker status:

```powershell
Write-Host "Checking Docker..." -ForegroundColor Cyan
docker --version
docker-compose --version
Write-Host "`nChecking Docker daemon..." -ForegroundColor Cyan
docker info
Write-Host "`nChecking running containers..." -ForegroundColor Cyan
docker ps
Write-Host "`nDocker is working!" -ForegroundColor Green
```

If any command fails, apply the solutions above.


