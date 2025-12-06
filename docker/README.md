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
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9091

### Testnet Setup

For a complete multi-node testnet:

```bash
cp .env.example .env
cd docker/testnet
docker compose up -d
```

This starts:
- 1 Bootstrap node (mining enabled)
- 2 Peer nodes
- PostgreSQL database
- Redis cache
- Prometheus + Grafana monitoring
- Block explorer

### Monitoring Validation Workflow

Use this when you need a locally running node plus Prometheus/Grafana to exercise new dashboards or alert rules.

1. **Copy the default env file** (needed by several containers):

   ```bash
   cp .env.example .env
   ```

2. **Start the testnet stack**. If port `9091` is already in use on your workstation, scale `xai-testnet-node1` to zero so only the bootstrap node and node2 expose metrics ports:

   ```bash
   cd docker/testnet
   docker compose up -d --scale xai-testnet-node1=0
   ```

   Exposed ports (all on localhost):
   - Bootstrap API/WebSocket: `8080/8081`
   - Bootstrap Prometheus exporter: `9090`
   - Node2 API: `8085`
   - Node2 Prometheus exporter: `9092`
   - Postgres: `5433`
   - Redis: `6380`
   - Prometheus UI: `9093`
   - Grafana UI: `3001`
   - Explorer UI: `8082`

3. **Verify containers are healthy**:

   ```bash
   docker ps
   # Expect: xai-testnet-bootstrap, xai-testnet-node2, postgres, redis, prometheus, grafana, explorer
   ```

4. **Generate `/send` rejection metrics** so the new dashboard panels/alerts have data:

   ```bash
   # Stale timestamp
   curl -s -X POST http://localhost:8080/send \
     -H "Content-Type: application/json" \
     -d '{"sender":"XAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA","recipient":"XAIBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB","amount":1,"fee":0.001,"public_key":"04CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC","nonce":1,"signature":"ABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABAB","timestamp":1000}'

   # TXID mismatch (set timestamp to current time)
   curl -s -X POST http://localhost:8080/send \
     -H "Content-Type: application/json" \
     -d '{"sender":"XAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA","recipient":"XAIBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB","amount":1,"fee":0.001,"public_key":"04CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC","nonce":2,"signature":"ABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABAB","timestamp":'$(date +%s)',"txid":"deadbeef"}'
   ```

   Each failing request increments `xai_send_rejections_*` counters.

5. **Inspect dashboards/alerts**:
   - Grafana: http://localhost:3001 (default credentials `admin/admin`). Open the “Security Operations” dashboard and look for the “/send Rejections by Reason” panel.
   - Prometheus rules: http://localhost:9093/rules (the `SendTimestampDrift` alert transitions to `pending` after a few samples).

6. **Stop the stack when finished**:

   ```bash
   docker compose down
   ```

   If you scaled node1 to zero when starting, the `down` command tears everything down (no need to repeat the `--scale` flag).

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

Access Grafana at http://localhost:3000 (admin/admin)

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
