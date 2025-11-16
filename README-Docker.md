# Docker Deployment Guide

This project provides complete Docker support, including backend, frontend, and Redis services.

## Quick Start

### 1. Using Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### 2. Build and Run Individually

#### Backend

```bash
cd backend
docker build -t pv-simulator-backend .
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/uploads:/app/uploads \
  --name pv-simulator-backend \
  pv-simulator-backend
```

#### Frontend

```bash
cd frontend
docker build -t pv-simulator-frontend .
docker run -d \
  -p 3000:80 \
  --name pv-simulator-frontend \
  pv-simulator-frontend
```

## Environment Variables

Create a `.env` file in the project root:

```env
# Backend configuration
SECRET_KEY=your-secret-key-here
DEBUG=False
DATABASE_URL=sqlite:///app/data/pv_simulator.db
REDIS_URL=redis://redis:6379/0

# API Keys (optional)
NASA_SSE_API_KEY=your-nasa-key
METEONORM_API_KEY=your-meteonorm-key
WEATHER_API_KEY=your-weather-key
```

## Service Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Redis**: localhost:6379

## Development Mode

For development environment, you can use override configuration:

```bash
# Copy example file
cp .docker-compose.override.yml.example .docker-compose.override.yml

# Start development environment (with hot reload)
docker-compose up
```

## Production Deployment

### 1. Build Production Images

```bash
# Build all services
docker-compose build

# Or build individually
docker-compose build backend frontend
```

### 2. Use Environment Variables

```bash
# Set environment variables
export SECRET_KEY=your-production-secret-key
export DEBUG=False

# Start services
docker-compose up -d
```

### 3. Use Docker Swarm or Kubernetes

For production environments, it's recommended to use Docker Swarm or Kubernetes for orchestration.

## Data Persistence

Data is stored in the following locations:

- **Database**: `./backend/data/pv_simulator.db`
- **Uploaded files**: `./backend/uploads/`
- **Redis data**: Docker volume `redis-data`

## Health Checks

All services are configured with health checks:

```bash
# Check service status
docker-compose ps

# View health check logs
docker inspect pv-simulator-backend | grep Health -A 10
```

## Troubleshooting

### View Logs

```bash
# All service logs
docker-compose logs

# Specific service logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs redis
```

### Enter Container

```bash
# Enter backend container
docker-compose exec backend bash

# Enter frontend container
docker-compose exec frontend sh
```

### Rebuild Services

```bash
# Force rebuild
docker-compose build --no-cache

# Recreate containers
docker-compose up -d --force-recreate
```

## Performance Optimization

### Backend

- Use multi-worker mode (default 4 workers)
- Configure Redis caching
- Use production-grade WSGI server (e.g., gunicorn + uvicorn workers)

### Frontend

- Use Nginx to serve static files
- Enable Gzip compression
- Configure static resource caching

## Security Recommendations

1. **Change default secret key**: Set a strong `SECRET_KEY` in production
2. **Limit network access**: Use firewall to restrict port access
3. **Use HTTPS**: Configure SSL/TLS in production
4. **Regular updates**: Keep Docker images and dependencies updated
5. **Non-root user**: All containers run as non-root users

## Common Issues

### Port Conflicts

If ports are occupied, modify port mappings in `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Change 8000 to 8001
```

### Database Initialization

The database will be created automatically on first run. To initialize data:

```bash
docker-compose exec backend python init_database.py
```

### Insufficient Memory

If you encounter memory issues during build, increase Docker's memory limit or use swap space.
