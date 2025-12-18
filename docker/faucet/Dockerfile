# XAI Testnet Faucet - Dockerfile

FROM python:3.11-slim

LABEL maintainer="XAI Blockchain Team"
LABEL description="XAI Testnet Faucet for Development"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    FAUCET_PORT=8086

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir flask requests

# Create non-root user
RUN groupadd -r faucet -g 1002 && \
    useradd -r -u 1002 -g faucet -m -d /home/faucet faucet

WORKDIR /app

# Copy faucet application
COPY --chown=faucet:faucet faucet.py ./

USER faucet

EXPOSE 8086

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8086/health || exit 1

CMD ["python", "faucet.py"]
