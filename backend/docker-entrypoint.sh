#!/bin/bash
set -e

# Fix permissions for mounted volumes (run as root)
# Fix database file permissions
if [ -f /app/pv_simulator.db ]; then
    chmod 666 /app/pv_simulator.db || true
    chown appuser:appuser /app/pv_simulator.db || true
fi

# Fix uploads directory permissions
if [ -d /app/uploads ]; then
    chmod -R 777 /app/uploads || true
    chown -R appuser:appuser /app/uploads || true
fi

# Switch to appuser and execute the main command
exec gosu appuser "$@"

