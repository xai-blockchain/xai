# XAI Block Explorer - Dockerfile

FROM python:3.11-slim

LABEL maintainer="XAI Blockchain Team"
LABEL description="XAI Block Explorer Web Interface"

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    EXPLORER_PORT=8087

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r explorer -g 1001 && \
    useradd -r -u 1001 -g explorer -m -d /home/explorer explorer

WORKDIR /app

# Copy requirements and install
COPY src/xai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=explorer:explorer src/xai/explorer.py ./
COPY --chown=explorer:explorer src/xai/block_explorer.py ./
COPY --chown=explorer:explorer src/xai/templates/ ./templates/
COPY --chown=explorer:explorer src/xai/core/ ./core/

USER explorer

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${EXPLORER_PORT}/health || exit 1

EXPOSE 8087

CMD ["python", "explorer.py"]
