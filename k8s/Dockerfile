# Multi-stage build for XAI Blockchain Node

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Create Python virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Set labels
LABEL maintainer="XAI Blockchain"
LABEL description="XAI Blockchain Node - Production Docker Image"
LABEL version="1.0.0"

# Create non-root user
RUN groupadd -r blockchain && useradd -r -g blockchain blockchain

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=blockchain:blockchain src /app/src
COPY --chown=blockchain:blockchain setup.py /app/
COPY --chown=blockchain:blockchain setup.cfg /app/

# Create necessary directories
RUN mkdir -p /data/blockchain /data/logs && \
    chown -R blockchain:blockchain /app /data

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Switch to non-root user
USER blockchain

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8546/health || exit 1

# Use tini as init process (handles signals properly)
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command
CMD ["python", "-m", "xai.core.node", \
     "--host", "0.0.0.0", \
     "--port", "8545"]

# Expose ports
EXPOSE 8545 8546 8547 9090

# Volume for persistent blockchain data
VOLUME ["/data/blockchain", "/data/logs"]
