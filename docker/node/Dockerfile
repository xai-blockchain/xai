# AIXN Blockchain Node - Node-Specific Dockerfile
# Optimized for standalone node deployment

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libssl-dev \
    libffi-dev \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt ./
COPY src/aixn/requirements.txt ./aixn-requirements.txt

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r aixn-requirements.txt

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.11-slim

# Metadata
LABEL maintainer="AIXN Blockchain Team"
LABEL description="AIXN Blockchain Node - Standalone Deployment"
LABEL version="1.0.0"

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    AIXN_ENV=production \
    AIXN_DATA_DIR=/data \
    AIXN_LOG_DIR=/logs \
    AIXN_CONFIG_DIR=/config \
    AIXN_NODE_PORT=8333 \
    AIXN_API_PORT=8080 \
    AIXN_METRICS_PORT=9090

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    netcat-openbsd \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r aixn -g 1000 && \
    useradd -r -u 1000 -g aixn -m -d /home/aixn -s /bin/bash aixn

# Create application directories
RUN mkdir -p \
    /app \
    /data/blockchain \
    /data/wallets \
    /data/state \
    /logs/node \
    /config && \
    chown -R aixn:aixn /app /data /logs /config

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=aixn:aixn src/ ./src/
COPY --chown=aixn:aixn config/ /config/

# Copy node-specific scripts
COPY --chown=aixn:aixn scripts/aixn_scripts/ ./scripts/
COPY --chown=aixn:aixn docker/node/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && \
    chown aixn:aixn /entrypoint.sh

# Switch to non-root user
USER aixn

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:${AIXN_API_PORT}/health || exit 1

# Expose ports
EXPOSE 8333 8080 9090

# Volume mounts
VOLUME ["/data", "/logs", "/config"]

# Entry point
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["node"]
