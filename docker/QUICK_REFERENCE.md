# XAI Blockchain Docker - Quick Reference Card

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit configuration
nano .env  # or your preferred editor

# 3. Start stack
docker-compose up -d

# 4. Check status
docker-compose ps
```

## Common Commands

### Service Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# View status
docker-compose ps

# Remove all (including volumes)
docker-compose down -v
```

### Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f xai-node

# Last 100 lines
docker-compose logs --tail=100 xai-node

# Search logs
docker-compose logs xai-node | grep ERROR
```

### Make Commands

```bash
make help           # Show all commands
make up             # Start services
make down           # Stop services
make logs           # View all logs
make logs-node      # View node logs
make health         # Check service health
make backup         # Create full backup
make clean          # Clean up resources
```

## Service URLs

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| Bootstrap API | http://localhost:12001 | - |
| Node1 API | http://localhost:12011 | - |
| Node2 API | http://localhost:12021 | - |
| Node3 API | http://localhost:12031 | - |
| Block Explorer | http://localhost:12080 | - |
| Grafana | http://localhost:12030 | admin/testnet123 |
| Prometheus | http://localhost:12090 | - |
| Faucet | http://localhost:12060 | - |
| PostgreSQL | testnet-postgres:5432 (internal) | xai_testnet/testnet_password |
| Redis | testnet-redis:6379 (internal) | - |

## Testnet

```bash
# Start testnet
cd docker/testnet && docker-compose up -d

# Or with make
make testnet-up

# View testnet logs
make testnet-logs

# Stop testnet
make testnet-down
```

### Testnet URLs

| Service | URL |
|---------|-----|
| Bootstrap Node | http://localhost:12001 |
| Node 1 | http://localhost:12011 |
| Node 2 | http://localhost:12021 |
| Node 3 | http://localhost:12031 |
| Explorer | http://localhost:12080 |
| Grafana | http://localhost:12030 |

- P2P websockets listen on 8765 in each container (host forwards 12002/12012/12022/12032); `XAI_NODE_PORT` is set to 8765 so logs match the actual listener.
- Peer diversity/geo limits are disabled in `docker/testnet/docker-compose.yml` (`XAI_P2P_*` zeros/high unknown threshold) to allow all validators to connect on the same local /16 with self-signed certs.

## Database

```bash
# Open PostgreSQL shell
docker-compose exec postgres psql -U xai -d xai_blockchain

# Backup database
docker-compose exec postgres pg_dump -U xai xai_blockchain > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U xai xai_blockchain

# Check database status
docker-compose exec postgres pg_isready
```

## Container Shell Access

```bash
# Node shell
docker-compose exec xai-node /bin/bash

# Database shell
docker-compose exec postgres /bin/bash

# Redis shell
docker-compose exec redis /bin/sh
```

## Monitoring

```bash
# View resource usage
docker stats

# Check health
curl http://localhost:12001/health

# Prometheus metrics
curl http://localhost:12070/metrics

# View specific service stats
docker stats xai-node
```

## Backup & Restore

```bash
# Full backup (Make)
make backup

# Manual database backup
docker-compose exec -T postgres pg_dump -U xai xai_blockchain > \
  backups/db-$(date +%Y%m%d).sql

# Manual blockchain backup
docker run --rm \
  -v crypto_blockchain-data:/data \
  -v $(pwd)/backups:/backup \
  ubuntu tar czf /backup/blockchain-$(date +%Y%m%d).tar.gz /data

# Restore database
make db-restore BACKUP=db-20250112.sql
```

## Troubleshooting

### Check Service Health

```bash
# All services
make health

# Individual checks
curl http://localhost:12001/health
docker-compose exec postgres pg_isready
docker-compose exec redis redis-cli ping
```

### View Logs for Errors

```bash
# Check recent errors
docker-compose logs --tail=50 xai-node | grep -i error

# Follow error logs
docker-compose logs -f xai-node | grep -i "error\|fail\|exception"
```

### Restart Specific Service

```bash
# Restart node only
docker-compose restart xai-node

# Restart database
docker-compose restart postgres
```

### Clean Up Resources

```bash
# Remove stopped containers
docker-compose down

# Remove volumes too
docker-compose down -v

# Clean all Docker resources
docker system prune -af --volumes
```

## Environment Variables

Essential `.env` variables:

```env
# Environment
XAI_ENV=development

# Database
POSTGRES_PASSWORD=secure_password

# Mining (optional)
XAI_ENABLE_MINING=false
XAI_MINING_ADDRESS=

# Logging
LOG_LEVEL=INFO
```

## Volume Management

```bash
# List volumes
docker volume ls | grep crypto

# Inspect volume
docker volume inspect crypto_blockchain-data

# Remove specific volume
docker volume rm crypto_blockchain-data

# Remove all unused volumes
docker volume prune
```

## Network Management

```bash
# List networks
docker network ls

# Inspect network
docker network inspect crypto_xai-network

# View container IPs
docker inspect -f '{{.Name}} - {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q)
```

## Image Management

```bash
# List images
docker images

# Pull latest images
docker-compose pull

# Build images
docker-compose build

# Remove unused images
docker image prune -a
```

## Production Deployment

```bash
# Start with production profile
docker-compose --profile production up -d

# Or using make
make prod-up

# View production logs
make prod-logs
```

## Common Issues & Solutions

### Container Won't Start
```bash
docker-compose logs [service-name]
docker-compose down && docker-compose up -d
```

### Database Connection Failed
```bash
docker-compose restart postgres
docker-compose exec postgres pg_isready
```

### Out of Disk Space
```bash
docker system df
docker system prune -af --volumes
```

### Port Already in Use
```bash
# Check what's using the port
netstat -ano | findstr :12001  # Windows
lsof -i :12001                 # Linux/Mac

# Change port in .env
XAI_API_PORT=12001
```

## Performance Tuning

### Add Resource Limits

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

### Optimize PostgreSQL

```bash
docker-compose exec postgres psql -U xai -d xai_blockchain -c \
  "ALTER SYSTEM SET shared_buffers = '512MB';"
docker-compose restart postgres
```

## Security Quick Checks

```bash
# Check exposed ports
docker-compose ps

# Review running processes
docker-compose top

# Check for updates
docker-compose pull

# Scan for vulnerabilities (requires Docker Scout)
docker scout cves xai-node
```

## API Quick Tests

```bash
# Health check
curl http://localhost:12001/health

# Get blockchain info
curl http://localhost:12001/api/v1/blockchain/info

# Get latest blocks
curl http://localhost:12001/api/v1/blocks?limit=10

# Get peers
curl http://localhost:12001/api/v1/peers
```

## Useful Docker Commands

```bash
# Remove all stopped containers
docker container prune

# Remove all unused images
docker image prune -a

# Remove all unused volumes
docker volume prune

# Remove all unused networks
docker network prune

# Complete cleanup
docker system prune -af --volumes
```

## File Locations

```
crypto/
├── Dockerfile                    # Main production image
├── docker-compose.yml            # Main orchestration
├── .dockerignore                 # Build exclusions
├── .env                          # Environment config
├── docker/
│   ├── node/
│   │   ├── Dockerfile           # Node-specific image
│   │   └── entrypoint.sh        # Startup script
│   ├── testnet/
│   │   └── docker-compose.yml   # Testnet setup
│   ├── monitoring/
│   │   └── prometheus.yml       # Metrics config
│   └── nginx/
│       └── nginx.conf           # Reverse proxy config
└── Makefile                      # Convenience commands
```

## Getting Help

```bash
# View all make commands
make help

# View docker-compose config
docker-compose config

# Check Docker version
docker --version
docker-compose --version

# View container details
docker inspect xai-node
```

---

**Quick Support:**
- Documentation: `docs/DOCKER_DEPLOYMENT.md`
- Issues: Issue Tracker
- Logs: `docker-compose logs -f`
