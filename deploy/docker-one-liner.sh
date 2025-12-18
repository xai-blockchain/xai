#!/bin/bash
#
# XAI Blockchain Node - Docker One-Liner Deployment
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/docker-one-liner.sh | bash
#
# This script deploys a single XAI node using Docker Compose on any system with Docker installed.
#

set -e

echo "========================================"
echo "XAI Blockchain Node - Docker Deployment"
echo "========================================"
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "Docker installed successfully"
    echo ""
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose not found. Installing..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed successfully"
    echo ""
fi

# Get parameters
read -p "Installation directory [/opt/xai]: " INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-/opt/xai}

read -p "Network mode (testnet/mainnet) [testnet]: " NETWORK_MODE
NETWORK_MODE=${NETWORK_MODE:-testnet}

read -p "API port [12001]: " API_PORT
API_PORT=${API_PORT:-12001}

read -p "P2P port [8765]: " P2P_PORT
P2P_PORT=${P2P_PORT:-8765}

read -p "Explorer port [12080]: " EXPLORER_PORT
EXPLORER_PORT=${EXPLORER_PORT:-12080}

# Confirm
echo ""
echo "Installation Configuration:"
echo "  Directory:      $INSTALL_DIR"
echo "  Network:        $NETWORK_MODE"
echo "  API Port:       $API_PORT"
echo "  P2P Port:       $P2P_PORT"
echo "  Explorer Port:  $EXPLORER_PORT"
echo ""
read -p "Continue? (yes/no) [yes]: " CONFIRM
CONFIRM=${CONFIRM:-yes}

if [ "$CONFIRM" != "yes" ]; then
    echo "Installation cancelled"
    exit 0
fi

# Create directory
echo ""
echo "Creating installation directory..."
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Clone repository
if [ -d ".git" ]; then
    echo "Repository already exists. Pulling latest..."
    git pull
else
    echo "Cloning XAI repository..."
    git clone https://github.com/xai-blockchain/xai.git .
fi

# Create environment file
echo ""
echo "Configuring environment..."
cat > .env <<EOF
XAI_NETWORK=$NETWORK_MODE
XAI_ENV=production
XAI_API_PORT=$API_PORT
XAI_NODE_PORT=$P2P_PORT
XAI_METRICS_PORT=12070
XAI_DEFAULT_HOST=0.0.0.0
POSTGRES_PASSWORD=$(openssl rand -hex 32)
POSTGRES_DB=xai_${NETWORK_MODE}
POSTGRES_USER=xai_${NETWORK_MODE}
REDIS_HOST=testnet-redis
POSTGRES_HOST=testnet-postgres
LOG_LEVEL=INFO
EOF

# Create docker-compose file for single node
echo ""
echo "Creating Docker Compose configuration..."
cat > docker-compose-standalone.yml <<'COMPOSE'
version: '3.8'

services:
  xai-node:
    build:
      context: .
      dockerfile: docker/node/Dockerfile
    container_name: xai-node
    restart: unless-stopped
    env_file: .env
    ports:
      - "${XAI_API_PORT:-12001}:${XAI_API_PORT:-12001}"
      - "${XAI_NODE_PORT:-8765}:${XAI_NODE_PORT:-8765}"
      - "${XAI_METRICS_PORT:-12070}:${XAI_METRICS_PORT:-12070}"
    volumes:
      - xai-data:/data
      - xai-logs:/logs
    networks:
      - xai-network
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${XAI_API_PORT:-12001}/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    container_name: xai-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-xai_testnet}
      POSTGRES_USER: ${POSTGRES_USER:-xai_testnet}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - xai-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-xai_testnet}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: xai-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb
    volumes:
      - redis-data:/data
    networks:
      - xai-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  explorer:
    build:
      context: .
      dockerfile: docker/explorer/Dockerfile
    container_name: xai-explorer
    restart: unless-stopped
    environment:
      XAI_API_URL: http://xai-node:${XAI_API_PORT:-12001}
      EXPLORER_PORT: 3000
    ports:
      - "${EXPLORER_PORT:-12080}:3000"
    networks:
      - xai-network
    depends_on:
      - xai-node

networks:
  xai-network:
    driver: bridge

volumes:
  xai-data:
  xai-logs:
  postgres-data:
  redis-data:
COMPOSE

# Start services
echo ""
echo "Starting XAI node..."
docker-compose -f docker-compose-standalone.yml up -d --build

echo ""
echo "Waiting for services to start..."
sleep 10

# Check status
if docker ps | grep -q xai-node; then
    echo ""
    echo "========================================"
    echo "XAI Node Deployed Successfully!"
    echo "========================================"
    echo ""
    echo "Services:"
    docker-compose -f docker-compose-standalone.yml ps
    echo ""
    echo "Access Points:"
    echo "  API:            http://localhost:$API_PORT"
    echo "  Health Check:   http://localhost:$API_PORT/health"
    echo "  Explorer:       http://localhost:$EXPLORER_PORT"
    echo "  Metrics:        http://localhost:12070/metrics"
    echo ""
    echo "Management Commands:"
    echo "  View logs:      docker logs -f xai-node"
    echo "  Stop:           docker-compose -f docker-compose-standalone.yml down"
    echo "  Restart:        docker-compose -f docker-compose-standalone.yml restart"
    echo "  Status:         docker-compose -f docker-compose-standalone.yml ps"
    echo ""
    echo "Data stored in Docker volumes: xai-data, xai-logs"
    echo ""
else
    echo ""
    echo "Error: Node failed to start"
    echo "Check logs: docker logs xai-node"
    exit 1
fi
