# AIXN Blockchain - Docker Deployment Guide

Complete guide for deploying AIXN blockchain using Docker and Docker Compose.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Deployment Scenarios](#deployment-scenarios)
6. [Architecture](#architecture)
7. [Monitoring & Observability](#monitoring--observability)
8. [Security](#security)
9. [Backup & Recovery](#backup--recovery)
10. [Troubleshooting](#troubleshooting)
11. [Production Checklist](#production-checklist)

## Overview

The AIXN blockchain Docker deployment provides:

- **Multi-stage builds** for optimized image sizes
- **Non-root user** execution for security
- **Health checks** for all services
- **Persistent volumes** for blockchain data
- **Complete monitoring stack** (Prometheus + Grafana)
- **Reverse proxy** with nginx for production
- **Multi-node testnet** support

## Prerequisites

### Software Requirements

- Docker Engine 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ ([Install Compose](https://docs.docker.com/compose/install/))
- Git (for cloning the repository)

### Hardware Requirements

**Minimum (Development):**
- 2 CPU cores
- 4GB RAM
- 20GB disk space

**Recommended (Production):**
- 4+ CPU cores
- 8GB+ RAM
- 100GB+ SSD storage
- Stable internet connection

### System Preparation

**Linux:**
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

**Windows:**
- Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- Enable WSL 2 backend
- Allocate sufficient resources in Docker Desktop settings

**macOS:**
- Install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- Allocate sufficient resources in Docker Desktop preferences

## Quick Start

### 1. Clone Repository

```bash
cd C:\Users\decri\GitClones\Crypto
# or
git clone https://github.com/aixn-blockchain/crypto.git
cd crypto
```

### 2. Create Environment File

```bash
# Copy example environment file
cp .env.example .env

# Edit with your configuration
# Windows: notepad .env
# Linux/Mac: nano .env
```

**Minimal `.env` configuration:**
```env
AIXN_ENV=development
POSTGRES_PASSWORD=secure_password_here
LOG_LEVEL=INFO
```

### 3. Start the Stack

Using Docker Compose:
```bash
docker-compose up -d
```

Using Make (recommended):
```bash
make up
```

### 4. Verify Deployment

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Check health
make health
```

### 5. Access Services

- **API**: http://localhost:8080
- **Block Explorer**: http://localhost:8082
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9091

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# ============================================================================
# Environment
# ============================================================================
AIXN_ENV=development
# Options: development, staging, production, testnet

# ============================================================================
# Node Configuration
# ============================================================================
AIXN_NODE_PORT=8333
AIXN_API_PORT=8080
AIXN_WS_PORT=8081
AIXN_METRICS_PORT=9090

# Network Settings
AIXN_NETWORK_ID=1
AIXN_MAX_PEERS=125
AIXN_MIN_PEERS=8

# Mining Settings
AIXN_ENABLE_MINING=false
AIXN_MINING_THREADS=2
AIXN_MINING_ADDRESS=

# ============================================================================
# Database
# ============================================================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=aixn_blockchain
POSTGRES_USER=aixn
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD

# ============================================================================
# Redis
# ============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# ============================================================================
# Monitoring
# ============================================================================
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO

# ============================================================================
# Security
# ============================================================================
AIXN_TLS_ENABLED=false
AIXN_API_KEY=
```

### Volume Configuration

Docker volumes are used for persistent data:

| Volume | Purpose | Path in Container |
|--------|---------|------------------|
| blockchain-data | Blockchain state | /data/blockchain |
| wallet-data | Wallet files | /data/wallets |
| postgres-data | Database | /var/lib/postgresql/data |
| redis-data | Cache | /data |
| prometheus-data | Metrics | /prometheus |
| grafana-data | Dashboards | /var/lib/grafana |
| node-logs | Application logs | /logs |

### Custom Configuration Files

Place custom configs in `config/`:
- `config/development.yaml` - Development settings
- `config/production.yaml` - Production settings
- `config/testnet.yaml` - Testnet settings

## Deployment Scenarios

### Scenario 1: Development Single Node

Minimal setup for local development:

```bash
# Start only essential services
docker-compose up -d aixn-node postgres redis

# View logs
docker-compose logs -f aixn-node
```

**Use case:** Local development, testing, debugging

### Scenario 2: Full Production Stack

Complete deployment with monitoring and reverse proxy:

```bash
# Start all services including nginx
docker-compose --profile production up -d

# Or using make
make prod-up
```

**Includes:**
- AIXN node
- PostgreSQL database
- Redis cache
- Prometheus monitoring
- Grafana visualization
- Block explorer
- Nginx reverse proxy

### Scenario 3: Multi-Node Testnet

Deploy a complete testnet with multiple interconnected nodes:

```bash
# Navigate to testnet directory
cd docker/testnet

# Start testnet
docker-compose up -d

# Or using make
make testnet-up
```

**Network topology:**
- 1 Bootstrap node (mining enabled)
- 2 Peer nodes
- Shared PostgreSQL database
- Shared Redis cache
- Complete monitoring stack

**Access testnet:**
- Bootstrap node: http://localhost:8080
- Node 1: http://localhost:8084
- Node 2: http://localhost:8085
- Explorer: http://localhost:8087

### Scenario 4: Mining Node

Deploy a dedicated mining node:

```bash
# Set mining environment variables
export AIXN_ENABLE_MINING=true
export AIXN_MINING_ADDRESS=your_wallet_address
export AIXN_MINING_THREADS=4

# Start node
docker-compose up -d aixn-node
```

Or edit `.env`:
```env
AIXN_ENABLE_MINING=true
AIXN_MINING_ADDRESS=AXN1234...
AIXN_MINING_THREADS=4
```

## Architecture

### Container Architecture

```
┌─────────────────────────────────────────────┐
│           Docker Host System                │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │   Docker Network: aixn-network       │  │
│  │   Subnet: 172.20.0.0/16              │  │
│  │                                      │  │
│  │  ┌────────────┐   ┌──────────────┐  │  │
│  │  │ AIXN Node  │   │  PostgreSQL  │  │  │
│  │  │            │───│              │  │  │
│  │  │ Port: 8333 │   │  Port: 5432  │  │  │
│  │  │ Port: 8080 │   └──────────────┘  │  │
│  │  └────────────┘                     │  │
│  │       │                              │  │
│  │       │    ┌──────────────┐          │  │
│  │       │────│    Redis     │          │  │
│  │       │    │ Port: 6379   │          │  │
│  │       │    └──────────────┘          │  │
│  │       │                              │  │
│  │       │    ┌──────────────┐          │  │
│  │       └────│  Prometheus  │          │  │
│  │            │ Port: 9091   │          │  │
│  │            └──────────────┘          │  │
│  │                   │                  │  │
│  │            ┌──────────────┐          │  │
│  │            │   Grafana    │          │  │
│  │            │ Port: 3000   │          │  │
│  │            └──────────────┘          │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Data Flow

```
External Request
      │
      ▼
┌─────────────┐
│   Nginx     │ (Production only)
│  Port: 80   │
│  Port: 443  │
└─────────────┘
      │
      ▼
┌─────────────┐
│  AIXN Node  │
│  REST API   │◄──┐
│  Port: 8080 │   │
└─────────────┘   │
      │           │
      ├───────────┼───────────┐
      │           │           │
      ▼           ▼           ▼
┌──────────┐ ┌────────┐ ┌──────────┐
│PostgreSQL│ │ Redis  │ │Prometheus│
│  State   │ │ Cache  │ │ Metrics  │
└──────────┘ └────────┘ └──────────┘
```

## Monitoring & Observability

### Prometheus Metrics

Access: http://localhost:9091

**Key metrics available:**
- `aixn_blocks_total` - Total blocks in chain
- `aixn_transactions_total` - Total transactions processed
- `aixn_peers_active` - Current peer count
- `aixn_block_time_seconds` - Average block time
- `aixn_mempool_size` - Pending transactions
- `aixn_wallet_balance` - Total wallet balances
- `go_memstats_alloc_bytes` - Memory usage
- `process_cpu_seconds_total` - CPU usage

**Sample queries:**
```promql
# Average block time over 1 hour
rate(aixn_block_time_seconds_sum[1h]) / rate(aixn_block_time_seconds_count[1h])

# Transactions per second
rate(aixn_transactions_total[5m])

# Peer connections trend
avg_over_time(aixn_peers_active[1h])
```

### Grafana Dashboards

Access: http://localhost:3000

**Default credentials:**
- Username: `admin`
- Password: `admin` (change immediately)

**Pre-configured dashboards:**
1. **Node Overview** - General health and performance
2. **Network Status** - Peer connections and synchronization
3. **Transaction Analysis** - Transaction volume and fees
4. **Mining Statistics** - Hash rate and block production
5. **System Resources** - CPU, memory, disk usage

### Logging

**View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f aixn-node

# Last 100 lines
docker-compose logs --tail=100 aixn-node

# With timestamps
docker-compose logs -f -t aixn-node
```

**Log locations:**
- Container logs: `docker-compose logs`
- Volume logs: `node-logs` volume mounted at `/logs`

**Log levels:**
- `DEBUG` - Verbose debugging (development only)
- `INFO` - General information (default)
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical failures

## Security

### Production Security Checklist

- [ ] **Change all default passwords**
  ```env
  POSTGRES_PASSWORD=strong_random_password
  GRAFANA_PASSWORD=different_strong_password
  ```

- [ ] **Enable TLS/SSL**
  ```env
  AIXN_TLS_ENABLED=true
  ```

- [ ] **Configure firewall rules**
  ```bash
  # Allow only necessary ports
  ufw allow 22/tcp   # SSH
  ufw allow 443/tcp  # HTTPS
  ufw allow 8333/tcp # P2P (optional)
  ufw enable
  ```

- [ ] **Set up SSL certificates**
  ```bash
  # Place in docker/nginx/ssl/
  cert.pem
  key.pem
  ```

- [ ] **Enable API authentication**
  ```env
  AIXN_API_KEY=generate_secure_random_key
  ```

- [ ] **Use read-only config mounts**
  ```yaml
  volumes:
    - ./config:/config:ro
  ```

- [ ] **Implement rate limiting** (configured in nginx)

- [ ] **Enable container resource limits**
  ```yaml
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
  ```

- [ ] **Regular security updates**
  ```bash
  docker-compose pull
  docker-compose up -d --force-recreate
  ```

- [ ] **Monitor security logs**
  ```bash
  docker-compose logs --grep "error\|failed\|unauthorized"
  ```

### Network Security

**Internal network isolation:**
- All services communicate via internal Docker network
- Only necessary ports exposed to host

**Firewall configuration (Ubuntu example):**
```bash
# Reset firewall
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# SSH access (adjust for your port)
ufw allow 22/tcp

# HTTPS (production)
ufw allow 443/tcp

# Optional: HTTP redirect
ufw allow 80/tcp

# Optional: P2P network (public node)
ufw allow 8333/tcp

# Enable firewall
ufw enable
ufw status verbose
```

### Secrets Management

**Never commit secrets to Git:**
```bash
# .gitignore already includes:
.env
*.key
*.pem
secure_keys/
```

**Use environment variables:**
```bash
# Read from secure vault or environment
export POSTGRES_PASSWORD=$(cat /run/secrets/db_password)
docker-compose up -d
```

**Docker secrets (Swarm mode):**
```yaml
secrets:
  db_password:
    external: true

services:
  postgres:
    secrets:
      - db_password
```

## Backup & Recovery

### Automated Backup Strategy

**Daily automated backup:**
```bash
# Add to crontab
0 2 * * * cd /path/to/crypto && make backup
```

**Backup script:**
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="backups"
DATE=$(date +%Y%m%d-%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U aixn aixn_blockchain > \
  $BACKUP_DIR/db-$DATE.sql

# Backup blockchain data
docker run --rm \
  -v crypto_blockchain-data:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  ubuntu tar czf /backup/blockchain-$DATE.tar.gz /data

# Backup wallets
docker run --rm \
  -v crypto_wallet-data:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  ubuntu tar czf /backup/wallets-$DATE.tar.gz /data

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Manual Backup

**Using Make:**
```bash
make backup
```

**Manual commands:**
```bash
# Backup database
docker-compose exec -T postgres pg_dump -U aixn aixn_blockchain > \
  backups/db-$(date +%Y%m%d).sql

# Backup blockchain volume
docker run --rm \
  -v crypto_blockchain-data:/data \
  -v $(pwd)/backups:/backup \
  ubuntu tar czf /backup/blockchain-$(date +%Y%m%d).tar.gz /data
```

### Restore from Backup

**Restore database:**
```bash
# Stop services
docker-compose down

# Restore database
cat backups/db-20250112.sql | \
  docker-compose exec -T postgres psql -U aixn aixn_blockchain

# Restart services
docker-compose up -d
```

**Restore blockchain data:**
```bash
# Stop services
docker-compose down

# Remove old volume
docker volume rm crypto_blockchain-data

# Create new volume
docker volume create crypto_blockchain-data

# Restore from backup
docker run --rm \
  -v crypto_blockchain-data:/data \
  -v $(pwd)/backups:/backup \
  ubuntu tar xzf /backup/blockchain-20250112.tar.gz -C /

# Restart services
docker-compose up -d
```

### Disaster Recovery

**Complete system recovery:**
```bash
# 1. Install Docker and Docker Compose on new system
# 2. Clone repository
git clone https://github.com/aixn-blockchain/crypto.git
cd crypto

# 3. Restore configuration
cp backup/.env .env

# 4. Create volumes
docker-compose up -d --no-start

# 5. Restore data
docker run --rm -v crypto_blockchain-data:/data -v $(pwd)/backups:/backup \
  ubuntu tar xzf /backup/blockchain-latest.tar.gz -C /

# 6. Restore database
cat backups/db-latest.sql | \
  docker-compose run --rm -T postgres psql -U aixn aixn_blockchain

# 7. Start services
docker-compose up -d

# 8. Verify
make health
```

## Troubleshooting

### Common Issues

#### Container Won't Start

**Symptoms:** Container exits immediately

**Solution:**
```bash
# Check logs
docker-compose logs aixn-node

# Check file permissions
docker-compose exec aixn-node ls -la /data

# Reset and restart
docker-compose down
docker volume rm crypto_blockchain-data
docker-compose up -d
```

#### Database Connection Failed

**Symptoms:** "could not connect to database"

**Solution:**
```bash
# Check database status
docker-compose exec postgres pg_isready -U aixn

# Restart database
docker-compose restart postgres

# Check credentials
docker-compose exec postgres psql -U aixn -d aixn_blockchain -c "SELECT 1"

# Reset database
docker-compose down postgres
docker volume rm crypto_postgres-data
docker-compose up -d postgres
```

#### Out of Disk Space

**Symptoms:** "no space left on device"

**Solution:**
```bash
# Check disk usage
df -h
docker system df -v

# Clean up Docker resources
docker system prune -a --volumes

# Remove old logs
docker-compose exec aixn-node find /logs -type f -mtime +7 -delete

# Increase disk allocation (Docker Desktop)
# Settings > Resources > Disk image size
```

#### Slow Synchronization

**Symptoms:** Blockchain sync is very slow

**Solution:**
```bash
# Check peer connections
curl http://localhost:8080/api/v1/peers

# Increase peer limit
# Edit .env:
AIXN_MAX_PEERS=200

# Restart node
docker-compose restart aixn-node

# Check network connectivity
docker-compose exec aixn-node ping 8.8.8.8
```

#### High Memory Usage

**Symptoms:** Container using too much memory

**Solution:**
```bash
# Check resource usage
docker stats

# Add memory limits to docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 4G

# Restart with limits
docker-compose up -d
```

### Debug Mode

Enable detailed logging:
```bash
# Set in .env
LOG_LEVEL=DEBUG
AIXN_DEBUG=true

# Restart
docker-compose restart aixn-node

# View debug logs
docker-compose logs -f aixn-node
```

### Health Checks

```bash
# Check all services
make health

# Individual health checks
curl http://localhost:8080/health
docker-compose exec postgres pg_isready
docker-compose exec redis redis-cli ping
```

## Production Checklist

### Pre-Deployment

- [ ] Review and update all configurations
- [ ] Set strong passwords for all services
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Configure backup strategy
- [ ] Test disaster recovery procedures
- [ ] Set up monitoring alerts
- [ ] Document deployment procedures
- [ ] Prepare rollback plan

### Deployment

- [ ] Create production `.env` file
- [ ] Build Docker images
- [ ] Start services with production profile
- [ ] Verify all health checks pass
- [ ] Test API endpoints
- [ ] Verify database connectivity
- [ ] Check monitoring dashboards
- [ ] Test backup procedures
- [ ] Document deployed version

### Post-Deployment

- [ ] Monitor system performance
- [ ] Check error logs daily
- [ ] Review security alerts
- [ ] Test failover procedures
- [ ] Update documentation
- [ ] Schedule maintenance windows
- [ ] Plan for scaling
- [ ] Review resource usage

### Maintenance Schedule

**Daily:**
- Monitor dashboards
- Check error logs
- Verify backups completed

**Weekly:**
- Review security alerts
- Check disk space
- Update dependencies
- Review performance metrics

**Monthly:**
- Security audit
- Update Docker images
- Test disaster recovery
- Review and optimize configurations

**Quarterly:**
- Major version upgrades
- Security penetration testing
- Architecture review
- Capacity planning

## Additional Resources

### Official Documentation

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

### AIXN Resources

- Project Repository: https://github.com/aixn-blockchain/crypto
- Documentation: `docs/` directory
- Issue Tracker: GitHub Issues
- Community: Discord/Telegram

### Support

For issues and questions:
- GitHub Issues: Report bugs and feature requests
- Documentation: Check `docs/` directory
- Community Forums: Ask questions and share knowledge

---

**Version:** 1.0
**Last Updated:** January 2025
**Maintained by:** AIXN Blockchain Team
