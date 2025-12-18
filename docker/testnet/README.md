# XAI Testnet - Docker Compose Quick Reference

Complete testnet configurations with block explorer and monitoring included by default.

## Quick Start (Recommended)

```bash
# Start full stack (4 nodes + explorer + monitoring)
docker compose -f docker-compose.full.yml up -d --build

# Verify all services
./verify_testnet_stack.sh

# Access services
# - Block Explorer: http://localhost:12080
# - Grafana:        http://localhost:12091 (admin/admin)
# - Node API:       http://localhost:12001
```

## Available Configurations

| File | Description | Best For |
|------|-------------|----------|
| `docker-compose.full.yml` | 4 nodes + explorer + monitoring | **Production testnet (RECOMMENDED)** |
| `docker-compose.yml` | Same as full.yml | Default configuration |
| `docker-compose.three-node.yml` | 3 nodes + explorer | Consensus debugging |
| `docker-compose.two-node.yml` | 2 nodes + explorer | Minimal testing |
| `docker-compose.one-node.yml` | 1 node + explorer | API development |
| `docker-compose.sentry.yml` | 4 validators + 2 sentry nodes | Public relay testing |

## Services Included

All configurations include:
- **Block Explorer** (http://localhost:12080) - Real-time blockchain viewer
- **Prometheus** (http://localhost:12090) - Metrics collection
- **Grafana** (http://localhost:12091) - Monitoring dashboards
- **PostgreSQL** - Blockchain data storage
- **Redis** - Caching layer

## Common Commands

```bash
# Start
docker compose -f docker-compose.full.yml up -d --build

# Stop
docker compose -f docker-compose.full.yml down

# Stop and remove all data
docker compose -f docker-compose.full.yml down -v

# View logs
docker compose logs -f xai-testnet-bootstrap
docker compose logs -f xai-testnet-explorer

# Check status
docker compose ps
./verify_testnet_stack.sh
```

## Health Checks

```bash
# Node health
curl http://localhost:12001/health

# Explorer health
curl http://localhost:12080/health

# Check consensus
for port in 12001 12011 12021 12031; do
  curl -s "http://localhost:$port/block/latest?summary=1" | jq '{height: .block_number, hash: .hash[0:16]}'
done
```

## Port Reference

| Service | Port | Description |
|---------|------|-------------|
| Bootstrap Node API | 12001 | Main API endpoint |
| Node 1 API | 12011 | Validator 1 API |
| Node 2 API | 12021 | Validator 2 API |
| Node 3 API | 12031 | Validator 3 API |
| **Block Explorer** | **12080** | **Web UI** |
| Grafana | 12091 | Monitoring dashboards |
| Prometheus | 12090 | Metrics collector |

## Troubleshooting

**Explorer not loading?**
```bash
curl http://localhost:12080/health
docker logs xai-testnet-explorer
```

**Nodes diverging?**
```bash
docker restart xai-testnet-node1
./verify_testnet_stack.sh
```

**Reset everything:**
```bash
docker compose down -v
docker system prune -f
docker compose up -d --build
```

## Documentation

See [TESTNET_SETUP.md](./TESTNET_SETUP.md) for detailed setup instructions, configuration options, and advanced usage.
