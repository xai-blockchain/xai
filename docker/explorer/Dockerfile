# XAI Block Explorer - Dockerfile

FROM python:3.11-slim

LABEL maintainer="XAI Blockchain Team"
LABEL description="XAI Block Explorer Web Interface"

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    EXPLORER_PORT=8082

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    pkg-config \
    build-essential \
    libsecp256k1-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r explorer -g 1001 && \
    useradd -r -u 1001 -g explorer -m -d /home/explorer explorer

WORKDIR /app

# Copy requirements and install
COPY constraints.txt /constraints.txt
COPY src/xai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application - maintain xai package structure
COPY --chown=explorer:explorer src/ ./src/
COPY --chown=explorer:explorer src/xai/templates/ ./templates/

USER explorer

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${EXPLORER_PORT}/health || exit 1

EXPOSE ${EXPLORER_PORT}

CMD ["python", "src/xai/explorer.py"]
