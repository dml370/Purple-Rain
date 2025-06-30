# Final Dockerfile for AI Companion (Optimized for Production)
# Target Platform: Oracle Cloud Linux (ARM/AARCH64)
# Final Version: June 29, 2025

# Use a specific, modern, and slim base image for the ARM64 architecture.
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PORT=8000
# Set the library path for the Oracle Instant Client so Python can find it.
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_12

# Install system dependencies, including Oracle prerequisites and build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    unzip \
    libaio1 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# --- Install Oracle Instant Client for ARM64 ---
# This is required for the python-oracledb library to run in Thick mode with a wallet.
RUN mkdir -p /opt/oracle
WORKDIR /opt/oracle
# Download the specific ARM64 version of the Instant Client
RUN curl -o instantclient-basiclite-linux.arm64-21.12.0.0.0dbru.zip https://download.oracle.com/otn_software/linux/instantclient/2112000/instantclient-basiclite-linux.arm64-21.12.0.0.0dbru.zip && \
    unzip instantclient-basiclite-linux.arm64-21.12.0.0.0dbru.zip && \
    # Clean up the downloaded zip file to keep the image slim
    rm instantclient-basiclite-linux.arm64-21.12.0.0.0dbru.zip
# Return to the main application working directory
WORKDIR /app

# Copy requirements file first to leverage Docker's build cache
COPY requirements.txt .

# Install Python dependencies from the pinned requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Create a non-root user and group for security
RUN adduser --system --group appuser && \
    chown -R appuser:appuser /app
# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Health check to ensure the container is running properly before accepting traffic
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/detailed || exit 1

# Start command using Gunicorn with Gevent workers for WebSocket support
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--worker-class", "gevent", "--timeout", "120", "app:app"]
