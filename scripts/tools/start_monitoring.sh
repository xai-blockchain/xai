#!/bin/bash
# XAI Blockchain - Start Monitoring Stack
# Starts Prometheus, Grafana, and Alertmanager using Docker Compose

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROMETHEUS_DIR="$SCRIPT_DIR/../../prometheus"

echo "=========================================="
echo "XAI Blockchain - Monitoring Stack"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker from https://www.docker.com/get-started"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
    exit 1
fi

# Navigate to prometheus directory
cd "$PROMETHEUS_DIR"

echo "Starting monitoring stack..."
echo ""

# Use docker compose (new syntax) or docker-compose (old syntax)
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Start containers
$COMPOSE_CMD up -d

echo ""
echo "✓ Monitoring stack started successfully!"
echo ""
echo "Access points:"
echo "  Prometheus:    http://localhost:9090"
echo "  Grafana:       http://localhost:3000 (admin/admin)"
echo "  Alertmanager:  http://localhost:9093"
echo ""
echo "To view logs:"
echo "  $COMPOSE_CMD logs -f"
echo ""
echo "To stop:"
echo "  $COMPOSE_CMD down"
echo ""
