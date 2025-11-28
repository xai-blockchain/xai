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

# Create non-root user
RUN groupadd -r faucet -g 1002 && \
    useradd -r -u 1002 -g faucet -m -d /home/faucet faucet

WORKDIR /app

# Copy requirements
COPY src/xai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy faucet application (placeholder - create if needed)
COPY --chown=faucet:faucet docker/faucet/faucet.py ./

USER faucet

EXPOSE 8086

CMD ["python", "faucet.py"]
