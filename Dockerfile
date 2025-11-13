# AIXN Blockchain Node - Production Dockerfile
# Multi-stage build for optimized image size and security

# ============================================================================
# Stage 1: Builder - Compile dependencies and prepare application
# ============================================================================
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY src/aixn/requirements.txt ./aixn-requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r aixn-requirements.txt

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim

# Metadata labels
LABEL maintainer="AIXN Blockchain Team"
LABEL description="AIXN Blockchain Node - Production Ready"
LABEL version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/aixn-blockchain/crypto"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/src \
    AIXN_ENV=production \
    AIXN_DATA_DIR=/data \
    AIXN_LOG_DIR=/logs \
    AIXN_CONFIG_DIR=/config

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r aixn -g 1000 && \
    useradd -r -u 1000 -g aixn -m -d /home/aixn -s /bin/bash aixn && \
    mkdir -p /app /data /logs /config && \
    chown -R aixn:aixn /app /data /logs /config

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (only what's needed for runtime)
COPY --chown=aixn:aixn src/ ./src/

# Create necessary directories with proper permissions
RUN mkdir -p \
    /data/blockchain \
    /data/wallets \
    /data/crypto_deposits \
    /data/gamification_data \
    /data/mining_data \
    /logs/node \
    /logs/api \
    /logs/monitoring && \
    chown -R aixn:aixn /data /logs /config

# Switch to non-root user
USER aixn

# Health check - check if node is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${AIXN_API_PORT:-8080}/health || exit 1

# Expose ports
# 8333 - P2P network port
# 8080 - REST API port
# 8081 - WebSocket API port
# 9090 - Prometheus metrics port
EXPOSE 8333 8080 8081 9090

# Volume mounts for persistent data
VOLUME ["/data", "/logs", "/config"]

# Default command - start AIXN node
CMD ["python", "-m", "src.aixn.core.node"]
