# Docker Setup Guide

## Prerequisites

Before using Docker with this project, you need to install Docker Desktop.

### Install Docker Desktop

1. **Download Docker Desktop**
   - Visit: https://www.docker.com/products/docker-desktop
   - Download the installer for Windows

2. **Install Docker Desktop**
   - Run the installer
   - Follow the installation wizard
   - Restart your computer if prompted

3. **Start Docker Desktop**
   - Launch Docker Desktop from the Start menu
   - Wait for Docker to start (you'll see a Docker icon in the system tray)
   - Make sure the Docker icon shows "Docker Desktop is running"

### Verify Installation

Open PowerShell or Command Prompt and run:

```bash
docker --version
docker-compose --version
```

You should see version numbers for both commands.

## Quick Start

Once Docker Desktop is running:

1. **Start services**
   ```bash
   .\docker-start.bat
   # or
   .\docker-start.ps1
   ```

2. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

3. **Stop services**
   ```bash
   .\docker-stop.bat
   # or
   .\docker-stop.ps1
   ```

## Troubleshooting

### Docker is not running

**Problem**: Script shows "Docker is not running"

**Solution**:
1. Open Docker Desktop from the Start menu
2. Wait for Docker to fully start (check system tray icon)
3. Try running the script again

### Docker command not found

**Problem**: Script shows "Docker is not installed"

**Solution**:
1. Install Docker Desktop (see above)
2. Make sure Docker Desktop is added to PATH during installation
3. Restart your terminal/PowerShell after installation
4. Verify with `docker --version`

### Port already in use

**Problem**: Error about ports 3000, 8000, or 6379 already in use

**Solution**:
1. Stop the service using the port:
   ```bash
   # Check what's using the port
   netstat -ano | findstr :8000
   ```
2. Or modify `docker-compose.yml` to use different ports:
   ```yaml
   ports:
     - "8001:8000"  # Change 8000 to 8001
   ```

### Build fails

**Problem**: Docker build fails with errors

**Solution**:
1. Check Docker Desktop has enough resources:
   - Open Docker Desktop Settings
   - Go to Resources
   - Increase Memory and CPU allocation
2. Check internet connection (needed to download images)
3. Try rebuilding:
   ```bash
   docker-compose build --no-cache
   ```

### Services won't start

**Problem**: Services start but immediately stop

**Solution**:
1. Check logs:
   ```bash
   docker-compose logs
   ```
2. Check service status:
   ```bash
   docker-compose ps
   ```
3. Check Docker Desktop resources are sufficient

## Manual Commands

If you prefer to use Docker commands directly:

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Need Help?

If you continue to have issues:
1. Check Docker Desktop is running
2. Review the error messages in the terminal
3. Check Docker Desktop logs (Settings > Troubleshoot)
4. Ensure you have sufficient system resources (RAM, disk space)



