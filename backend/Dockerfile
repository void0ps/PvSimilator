# Multi-stage build - Build stage
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Configure pip to use Chinese mirror (optional)
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ || true

# Copy dependency file
COPY requirements.txt .

# Install Python dependencies to user directory
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install runtime dependencies (including gosu for user switching)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user first
RUN useradd -m -u 1000 appuser

# Copy Python packages from build stage to appuser's home
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Set PATH to use locally installed packages
ENV PATH=/home/appuser/.local/bin:$PATH

# Create application directory
WORKDIR /app

# Create necessary directories with proper ownership
RUN mkdir -p /app/uploads /app/data && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Copy and set up entrypoint script (needs to run as root to fix permissions)
COPY --chown=root:root docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Keep as root for entrypoint, it will switch to appuser
# USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Use entrypoint to fix permissions at runtime
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Start command (use single worker for SQLite compatibility)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
