# XAI Blockchain - Docker Deployment Guide

This directory contains Docker configurations for deploying XAI blockchain nodes in various environments.

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Deployment Scenarios](#deployment-scenarios)
- [Monitoring](#monitoring)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available
- 20GB disk space for blockchain data

### Development Setup

1. **Clone the repository and navigate to the project root:**

```bash
cd C:\Users\decri\GitClones\Crypto
```

2. **Copy the environment file:**

```bash
cp .env.example .env
```

3. **Edit `.env` with your configuration:**

```bash
# Minimal development configuration
XAI_ENV=development
LOG_LEVEL=DEBUG
POSTGRES_PASSWORD=your_secure_password
```

4. **Start the stack:**

```bash
docker-compose up -d
```

5. **Check node status:**

```bash
docker-compose logs -f xai-node
```

6. **Access services:**

- API: http://localhost:8080
- Block Explorer: http://localhost:8082
- Grafana: http://localhost:12030
- Prometheus: http://localhost:9091

### Testnet Setup

For detailed testnet setup instructions with proven consensus configurations, see **[docker/testnet/TESTNET_SETUP.md](testnet/TESTNET_SETUP.md)**.

#### Quick Start Options

```bash
cd docker/testnet

# 1-Node (development/API testing)
docker compose -f docker-compose.one-node.yml up -d --build

# 2-Node (minimal consensus testing)
docker compose -f docker-compose.two-node.yml up -d --build

# 3-Node (recommended for consensus debugging - 100% consensus)
docker compose -f docker-compose.three-node.yml up -d --build

# 4-Node (full mesh network - 98%+ consensus)
docker compose -f docker-compose.four-node.yml up -d --build

# Sentry nodes (public relay testing)
docker compose -f docker-compose.sentry.yml up -d --build
```

#### Available Configurations

| Configuration | Nodes | Use Case | Expected Consensus |
|--------------|-------|----------|-------------------|
| `docker-compose.one-node.yml` | 1 | Development, API testing | N/A |
| `docker-compose.two-node.yml` | 2 | Minimal consensus testing | 100% |
| `docker-compose.three-node.yml` | 3 | Consensus debugging | 100% |
| `docker-compose.four-node.yml` | 4 | Full mesh connectivity | 98%+ |
| `docker-compose.sentry.yml` | 4+2 | Validator + relay nodes | 98%+ |

#### Port Allocations

| Node | API | P2P | Metrics |
|------|-----|-----|---------|
| Bootstrap | 12001 | 12002 | 12070 |
| Node 1 | 12011 | 12012 | 12071 |
| Node 2 | 12021 | 12022 | 12072 |
| Node 3 | 12031 | 12032 | 12073 |
| Sentry 1 | 12041 | 12042 | 12074 |
| Sentry 2 | 12051 | 12052 | 12075 |
| Explorer | 12080 | - | - |

**Note:** All configurations use subnet 172.30.1.0/24 with gateway 172.30.1.1.

### Monitoring and Verification

Use these commands to verify testnet health:

```bash
# Check node health (replace PORT with actual port)
curl http://localhost:12001/health

# Compare block heights across nodes
for port in 12001 12011 12021 12031; do
  echo "Port $port: $(curl -s \"http://localhost:$port/block/latest?summary=1\" | jq '{height: .block_number, hash: .hash[0:16]}')"
done

# View container logs
docker logs xai-testnet-bootstrap -f --tail 100
```

For detailed monitoring setup with Prometheus and Grafana, see the monitoring configurations in `docker/testnet/monitoring/`.

## Architecture

### Container Structure

```
xai-blockchain/
├── xai-node          # Main blockchain node
├── postgres           # PostgreSQL database
├── redis              # Cache & message broker
├── prometheus         # Metrics collection
├── grafana            # Metrics visualization
├── block-explorer     # Web interface
└── nginx              # Reverse proxy (production)
```

### Network Architecture

```
┌─────────────────────────────────────────────┐
│              Internet / Users               │
└────────────────┬────────────────────────────┘
                 │
        ┌────────▼────────┐
        │  Nginx (443)    │ SSL Termination
        │  Rate Limiting  │
        └────────┬────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼────┐            ┌───────▼──────┐
│ XAI   │            │ Block        │
│ Node   │◄───────────┤ Explorer     │
│ (8080) │            │ (8082)       │
└───┬────┘            └──────────────┘
    │
    ├──────┬──────┬─────────┐
    │      │      │         │
┌───▼──┐ ┌─▼───┐ ┌▼──────┐ ┌▼────────┐
│ DB   │ │Redis│ │Prom   │ │Grafana  │
│ 5432 │ │6379 │ │9090   │ │3000     │
└──────┘ └─────┘ └───────┘ └─────────┘
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `XAI_ENV` | Environment (development/production/testnet) | development |
| `XAI_NODE_PORT` | P2P network port | 8333 |
| `XAI_API_PORT` | REST API port | 8080 |
| `XAI_ENABLE_MINING` | Enable mining | false |
| `POSTGRES_PASSWORD` | Database password | Required |
| `LOG_LEVEL` | Logging level | INFO |

### Volume Mounts

Persistent data is stored in Docker volumes:

| Volume | Purpose | Size |
|--------|---------|------|
| `blockchain-data` | Blockchain state | ~10GB+ |
| `wallet-data` | Wallet files | ~100MB |
| `postgres-data` | Database | ~5GB+ |
| `prometheus-data` | Metrics | ~1GB |
| `grafana-data` | Dashboards | ~100MB |

## Deployment Scenarios

### 1. Single Node (Development)

```bash
docker-compose up -d xai-node postgres redis
```

Minimal setup for development and testing.

### 2. Full Stack (Production)

```bash
docker-compose --profile production up -d
```

Includes monitoring, explorer, and nginx reverse proxy.

### 3. Multi-Node Testnet

```bash
cd docker/testnet
docker-compose up -d
```

Three interconnected nodes for network testing.

### 4. Mining Node

```bash
XAI_ENABLE_MINING=true \
XAI_MINING_ADDRESS=your_address \
XAI_MINING_THREADS=4 \
docker-compose up -d xai-node
```

## Monitoring

### Prometheus Metrics

Access Prometheus at http://localhost:9091

Key metrics:
- `xai_blocks_total` - Total blocks mined
- `xai_transactions_total` - Total transactions
- `xai_peers_active` - Active peer connections
- `xai_block_time_seconds` - Block generation time

### Grafana Dashboards

Access Grafana at http://localhost:12030 (admin/admin)

Pre-configured dashboards:
- **Node Overview**: General node health
- **Network Status**: Peer connections and sync status
- **Transaction Pool**: Mempool statistics
- **Mining Performance**: Hash rate and block times

### Health Checks

Check service health:

```bash
# Node health
curl http://localhost:8080/health

# Database health
docker-compose exec postgres pg_isready

# Redis health
docker-compose exec redis redis-cli ping
```

## Security

### Production Checklist

- [ ] Change all default passwords in `.env`
- [ ] Enable TLS (`XAI_TLS_ENABLED=true`)
- [ ] Configure firewall rules
- [ ] Set up API key authentication
- [ ] Enable rate limiting in nginx
- [ ] Use read-only config mounts
- [ ] Implement backup strategy
- [ ] Configure SSL certificates
- [ ] Enable container resource limits
- [ ] Review log access permissions

### SSL Configuration

For production with SSL:

1. Place certificates in `docker/nginx/ssl/`:
   - `cert.pem` - SSL certificate
   - `key.pem` - Private key

2. Update nginx configuration in `docker/nginx/nginx.conf`

3. Enable HTTPS redirect in nginx config

### Network Security

Firewall rules (example for Ubuntu):

```bash
# Allow SSH
ufw allow 22/tcp

# Allow HTTPS
ufw allow 443/tcp

# Allow P2P (optional - only if public node)
ufw allow 8333/tcp

# Deny all other incoming
ufw default deny incoming
ufw enable
```

## Troubleshooting

### Common Issues

**Node won't start:**

```bash
# Check logs
docker-compose logs xai-node

# Verify permissions
docker-compose exec xai-node ls -la /data

# Reset and restart
docker-compose down
docker volume rm crypto_blockchain-data
docker-compose up -d
```

**Database connection failed:**

```bash
# Check database status
docker-compose exec postgres pg_isready

# Reset database
docker-compose down postgres
docker volume rm crypto_postgres-data
docker-compose up -d postgres
```

**Out of disk space:**

```bash
# Check volume usage
docker system df -v

# Clean up unused resources
docker system prune -a --volumes
```

**Slow synchronization:**

```bash
# Check peer connections
curl http://localhost:8080/api/v1/peers

# Increase peer limit
XAI_MAX_PEERS=200 docker-compose up -d

# Check network connectivity
docker-compose exec xai-node ping 8.8.8.8
```

### Logs

Access logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f xai-node

# Last 100 lines
docker-compose logs --tail=100 xai-node

# Follow with timestamps
docker-compose logs -f -t xai-node
```

### Performance Tuning

**Increase resources:**

Edit `docker-compose.yml`:

```yaml
services:
  xai-node:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

**Database optimization:**

```bash
# Increase PostgreSQL cache
docker-compose exec postgres psql -U xai -c \
  "ALTER SYSTEM SET shared_buffers = '512MB';"
docker-compose restart postgres
```

## Backup and Recovery

### Backup Strategy

```bash
# Backup blockchain data
docker run --rm \
  -v crypto_blockchain-data:/data \
  -v $(pwd)/backups:/backup \
  ubuntu tar czf /backup/blockchain-$(date +%Y%m%d).tar.gz /data

# Backup database
docker-compose exec postgres pg_dump -U xai xai_blockchain > \
  backups/db-$(date +%Y%m%d).sql
```

### Recovery

```bash
# Restore blockchain data
docker run --rm \
  -v crypto_blockchain-data:/data \
  -v $(pwd)/backups:/backup \
  ubuntu tar xzf /backup/blockchain-20250112.tar.gz -C /

# Restore database
cat backups/db-20250112.sql | \
  docker-compose exec -T postgres psql -U xai xai_blockchain
```

## Upgrading

### Update Containers

```bash
# Pull latest images
docker-compose pull

# Recreate containers
docker-compose up -d --force-recreate

# Remove old images
docker image prune -a
```

### Rolling Updates (Zero Downtime)

```bash
# Scale up with new version
docker-compose up -d --scale xai-node=2

# Wait for health check
sleep 30

# Remove old container
docker-compose up -d --scale xai-node=1
```

## Support

For issues and questions: use your organization’s issue tracker.
- Documentation: [Full Documentation](https://docs.xai.network)
- Community: [Discord Server](https://discord.gg/xai)

## License

See LICENSE file in project root.
