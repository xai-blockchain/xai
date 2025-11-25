# XAI Blockchain Node - Docker Container
# INTERNAL USE ONLY - DELETE BEFORE PUBLIC RELEASE

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy blockchain code
COPY . .

# Create data directories
RUN mkdir -p data logs gamification_data mining_data recovery_data exchange_data governance_data

# Expose ports
EXPOSE 5000

# Environment variables
ENV XAI_HOST=0.0.0.0
ENV XAI_PORT=5000
ENV XAI_NETWORK=mainnet

# Run node
CMD ["python", "core/node.py"]
