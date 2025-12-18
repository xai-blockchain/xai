# XAI Blockchain Testnet Setup Guide

This guide provides step-by-step instructions for deploying XAI blockchain testnets using Docker Compose. These configurations have been tested to achieve 98%+ consensus rates.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start Commands](#quick-start-commands)
- [Configuration Files](#configuration-files)
- [1-Node Setup](#1-node-setup)
- [2-Node Setup](#2-node-setup)
- [3-Node Setup](#3-node-setup)
- [4-Node Setup](#4-node-setup)
- [Sentry Node Setup](#sentry-node-setup)
- [Consensus Monitoring](#consensus-monitoring)
- [Troubleshooting](#troubleshooting)
- [Critical Configuration Settings](#critical-configuration-settings)

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available
- 20GB disk space for blockchain data
- No services running on ports 12000-12100

## Quick Start Commands

```bash
# Navigate to testnet directory
cd docker/testnet

# 1-Node (development/API testing)
docker compose -f docker-compose.one-node.yml up -d --build

# 2-Node (minimal consensus testing)
docker compose -f docker-compose.two-node.yml up -d --build

# 3-Node (recommended for consensus debugging)
docker compose -f docker-compose.three-node.yml up -d --build

# 4-Node (full mesh network testing)
docker compose -f docker-compose.four-node.yml up -d --build

# Sentry nodes (public relay testing)
docker compose -f docker-compose.sentry.yml up -d --build

# Stop and clean up
docker compose -f <config-file>.yml down -v
```

## Configuration Files

| File | Nodes | Use Case | Expected Consensus |
|------|-------|----------|-------------------|
| `docker-compose.one-node.yml` | 1 | Development, API testing | N/A (single node) |
| `docker-compose.two-node.yml` | 2 | Minimal consensus testing | 100% |
| `docker-compose.three-node.yml` | 3 | Consensus debugging | 100% |
| `docker-compose.four-node.yml` | 4 | Full mesh connectivity | 98%+ |
| `docker-compose.sentry.yml` | 4+2 | Public relay testing | 98%+ |
| `docker-compose.yml` | 4 + monitoring | Full stack with Prometheus/Grafana | 98%+ |
| `docker-compose.override.yml.example` | N/A | Customization template | N/A |

### Explorer Integration

All testnet configurations include a block explorer service by default, accessible at http://localhost:12080.

**To disable the explorer** (if not needed):

```bash
# Copy the example override file
cp docker-compose.override.yml.example docker-compose.override.yml

# Edit and uncomment the explorer profile section
# This makes the explorer optional - start with --profile explorer
docker compose -f docker-compose.three-node.yml --profile explorer up -d
```

## 1-Node Setup

Single node testnet for development and API testing.

### Start

```bash
cd docker/testnet
docker compose -f docker-compose.one-node.yml up -d --build
```

### Verify

```bash
# Check node health
curl http://localhost:12001/health

# Check block height
curl "http://localhost:12001/block/latest?summary=1"
```

### Access Points

| Service | URL |
|---------|-----|
| API | http://localhost:12001 |
| P2P WebSocket | ws://localhost:12002 |
| Metrics | http://localhost:12070 |
| Explorer | http://localhost:12080 |
| Grafana (monitoring) | http://localhost:12091 |
| Prometheus | http://localhost:12090 |

### Stop

```bash
docker compose -f docker-compose.one-node.yml down
# To remove data volumes:
docker compose -f docker-compose.one-node.yml down -v
```

## 2-Node Setup

Minimal multi-node testnet for basic consensus testing.

### Start

```bash
cd docker/testnet
docker compose -f docker-compose.two-node.yml up -d --build
```

### Verify

```bash
# Check both nodes
curl http://localhost:12001/health  # Bootstrap
curl http://localhost:12011/health  # Node 1

# Compare block heights
curl -s "http://localhost:12001/block/latest?summary=1" | jq '.block_number'
curl -s "http://localhost:12011/block/latest?summary=1" | jq '.block_number'
```

### Access Points

| Node | API | P2P | Metrics |
|------|-----|-----|---------|
| Bootstrap | 12001 | 12002 | 12070 |
| Node 1 | 12011 | 12012 | 12071 |
| Explorer | 12080 | - | - |

### Stop

```bash
docker compose -f docker-compose.two-node.yml down -v
```

## 3-Node Setup

Recommended for consensus debugging. This configuration has been tested to achieve 100% consensus.

### Start

```bash
cd docker/testnet
docker compose -f docker-compose.three-node.yml up -d --build
```

### Verify Consensus

```bash
# Check all nodes are responsive
for port in 12001 12011 12021; do
  echo "Port $port: $(curl -s http://localhost:$port/health | jq -r '.status')"
done

# Compare block heights and hashes
for port in 12001 12011 12021; do
  echo "Port $port: $(curl -s \"http://localhost:$port/block/latest?summary=1\" | jq '{height: .block_number, hash: .hash[0:16]}')"
done
```

### Access Points

| Node | API | P2P | Metrics |
|------|-----|-----|---------|
| Bootstrap | 12001 | 12002 | 12070 |
| Node 1 | 12011 | 12012 | 12071 |
| Node 2 | 12021 | 12022 | 12072 |
| Explorer | 12080 | - | - |

### Stop

```bash
docker compose -f docker-compose.three-node.yml down -v
```

## 4-Node Setup

Full mesh network for comprehensive consensus testing. Achieves 98%+ consensus rate.

### Start

```bash
cd docker/testnet
docker compose -f docker-compose.four-node.yml up -d --build
```

### Verify Consensus

```bash
# Quick consensus check
for port in 12001 12011 12021 12031; do
  echo "Port $port: $(curl -s http://localhost:$port/block/latest?summary=1 | jq '{height: .block_number, hash: .hash[0:16]}')"
done
```

### Run 20-Minute Consensus Test

```bash
# Create test script
cat > /tmp/consensus_test.sh << 'EOF'
#!/bin/bash
PORTS="12001 12011 12021 12031"
echo "Starting consensus monitoring..."
while true; do
  HEIGHTS=""
  HASHES=""
  for port in $PORTS; do
    DATA=$(curl -s "http://localhost:$port/block/latest?summary=1")
    HEIGHT=$(echo $DATA | jq -r '.block_number')
    HASH=$(echo $DATA | jq -r '.hash[0:16]')
    HEIGHTS="$HEIGHTS $HEIGHT"
    HASHES="$HASHES $HASH"
  done
  echo "$(date '+%H:%M:%S') Heights:$HEIGHTS Hashes:$HASHES"
  sleep 20
done
EOF
chmod +x /tmp/consensus_test.sh
/tmp/consensus_test.sh
```

### Automated Verification Harness

The repository ships with an automated verifier that hits every node's `/health`, `/stats`, and `/peers`
endpoints plus the explorer `/health` endpoint. It confirms consensus (matching heights + hashes),
minimum peer counts, and explorer readiness in a single run.

```bash
# From the repository root (after `docker compose ... up`)
python scripts/testnet/verify_four_node_network.py --min-peers 3

# JSON output for CI
python scripts/testnet/verify_four_node_network.py --json > /tmp/four-node-status.json
```

Flags:
- `--node NAME=URL` to override defaults (repeat for each node, defaults to localhost ports)
- `--min-peers` to adjust the peer threshold (default: 3 for a 4-node mesh)
- `--explorer-url` or `--skip-explorer` to control explorer checks
- `--json` for machine-readable output (non-zero exit code when any check fails)

### Access Points

| Node | API | P2P | Metrics |
|------|-----|-----|---------|
| Bootstrap | 12001 | 12002 | 12070 |
| Node 1 | 12011 | 12012 | 12071 |
| Node 2 | 12021 | 12022 | 12072 |
| Node 3 | 12031 | 12032 | 12073 |
| Explorer | 12080 | - | - |

### Stop

```bash
docker compose -f docker-compose.four-node.yml down -v
```

## Sentry Node Setup

Sentry nodes are non-mining relay nodes that protect validators and can accept public connections. Use this configuration for testing realistic network conditions.

### Architecture

```
                    [Public Network]
                          |
              +-----------+-----------+
              |                       |
         [Sentry 1]             [Sentry 2]
              |                       |
              +-----------+-----------+
                          |
              +-----------+-----------+
              |           |           |
         [Validator 1] [Validator 2] [Validator 3]
              |           |           |
              +-----------+-----------+
                          |
                    [Bootstrap]
```

### Start

```bash
cd docker/testnet
docker compose -f docker-compose.sentry.yml up -d --build
```

### Verify

```bash
# Check validator nodes
for port in 12001 12011 12021 12031; do
  echo "Validator $port: $(curl -s http://localhost:$port/health | jq -r '.status')"
done

# Check sentry nodes (relay only, non-mining)
for port in 12041 12051; do
  echo "Sentry $port: $(curl -s http://localhost:$port/health | jq -r '.status')"
done
```

### Access Points

| Node | Role | API | P2P | Metrics |
|------|------|-----|-----|---------|
| Bootstrap | Validator | 12001 | 12002 | 12070 |
| Node 1 | Validator | 12011 | 12012 | 12071 |
| Node 2 | Validator | 12021 | 12022 | 12072 |
| Node 3 | Validator | 12031 | 12032 | 12073 |
| Sentry 1 | Relay | 12041 | 12042 | 12074 |
| Sentry 2 | Relay | 12051 | 12052 | 12075 |
| Explorer | UI | 12080 | - | - |

### Stop

```bash
docker compose -f docker-compose.sentry.yml down -v
```

## Consensus Monitoring

### Quick Consensus Check Script

```bash
#!/bin/bash
# Save as check_consensus.sh

PORTS="${1:-12001 12011 12021 12031}"
echo "Checking consensus across ports: $PORTS"
echo "---"

declare -a HEIGHTS
declare -a HASHES

for port in $PORTS; do
  DATA=$(curl -s "http://localhost:$port/block/latest?summary=1" 2>/dev/null)
  if [ $? -eq 0 ] && [ -n "$DATA" ]; then
    HEIGHT=$(echo $DATA | jq -r '.block_number // "N/A"')
    HASH=$(echo $DATA | jq -r '.hash[0:16] // "N/A"')
    echo "Port $port: height=$HEIGHT hash=$HASH..."
    HEIGHTS+=("$HEIGHT")
    HASHES+=("$HASH")
  else
    echo "Port $port: UNREACHABLE"
  fi
done

# Check if all heights match
UNIQUE_HEIGHTS=$(printf '%s\n' "${HEIGHTS[@]}" | sort -u | wc -l)
UNIQUE_HASHES=$(printf '%s\n' "${HASHES[@]}" | sort -u | wc -l)

echo "---"
if [ "$UNIQUE_HEIGHTS" -eq 1 ] && [ "$UNIQUE_HASHES" -eq 1 ]; then
  echo "CONSENSUS: All nodes agree on height ${HEIGHTS[0]} and hash ${HASHES[0]}"
else
  echo "DIVERGED: $UNIQUE_HEIGHTS unique heights, $UNIQUE_HASHES unique hashes"
fi
```

### Prometheus Metrics

If monitoring is enabled, access Prometheus at http://localhost:12090 and Grafana at http://localhost:12030.

Key metrics:
- `xai_blocks_total` - Total blocks mined
- `xai_block_height` - Current block height
- `xai_peers_connected` - Number of connected peers
- `xai_mining_active` - Mining status (1=active, 0=paused)

## Troubleshooting

### Nodes Not Connecting

```bash
# Check container logs
docker logs xai-testnet-bootstrap 2>&1 | grep -i "peer\|connect\|error"
docker logs xai-testnet-node1 2>&1 | grep -i "peer\|connect\|error"

# Verify network connectivity
docker exec xai-testnet-bootstrap ping -c 3 xai-testnet-node1
```

### Consensus Divergence

If nodes are diverging frequently:

1. **Check mining cooldown**: Ensure `XAI_MINING_COOLDOWN_SECONDS: "10.0"` is set
2. **Verify signature settings**: `XAI_P2P_DEBUG_SIGNING: "1"` and `XAI_P2P_DISABLE_SIGNATURE_VERIFY: "0"`
3. **Check WebSocket settings**: Ping interval should be 20 seconds

```bash
# Force re-sync by restarting diverged node
docker restart xai-testnet-node1
```

### Database Connection Issues

```bash
# Check PostgreSQL
docker exec xai-testnet-postgres pg_isready -U xai_testnet

# Check Redis
docker exec xai-testnet-redis redis-cli ping
```

### Out of Disk Space

```bash
# Check Docker disk usage
docker system df

# Clean up unused resources
docker system prune -a --volumes
```

### Reset and Start Fresh

```bash
# Stop all containers and remove volumes
docker compose -f <config-file>.yml down -v

# Remove any dangling images
docker image prune -f

# Rebuild and start
docker compose -f <config-file>.yml up -d --build
```

## Critical Configuration Settings

These settings have been validated to achieve 98%+ consensus on 4-node networks:

### Mining Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| `XAI_FAST_MINING` | `"1"` | Enable fast mining for testnet |
| `XAI_ALLOW_EMPTY_MINING` | `"1"` (bootstrap only) | Allow empty blocks on bootstrap |
| `XAI_ALLOW_EMPTY_MINING` | `"0"` (other nodes) | Require transactions on peer nodes |
| `XAI_MINING_HEARTBEAT_SECONDS` | `"5"` | Mining status check interval |
| `XAI_MINING_COOLDOWN_SECONDS` | `"10.0"` | **CRITICAL**: Wait time after mining for propagation |

### P2P Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| `XAI_P2P_DEBUG_SIGNING` | `"1"` | Enable debug signing |
| `XAI_P2P_DISABLE_SIGNATURE_VERIFY` | `"0"` | **Keep signature verification enabled** |
| `XAI_P2P_PING_INTERVAL_SECONDS` | `"20"` | WebSocket keep-alive interval |
| `XAI_P2P_PING_TIMEOUT_SECONDS` | `"20"` | WebSocket ping timeout |
| `XAI_P2P_CLOSE_TIMEOUT_SECONDS` | `"10"` | Connection close timeout |
| `XAI_P2P_MONITOR_INTERVAL_SECONDS` | `"30"` | Peer monitoring interval |
| `XAI_P2P_SYNC_INTERVAL_SECONDS` | `"30"` | Block sync interval |
| `XAI_P2P_MAX_CONNECTIONS_PER_IP` | `"50"` | Allow multiple container connections |

### Geo/ASN Settings (Disabled for Local Testnet)

| Setting | Value | Purpose |
|---------|-------|---------|
| `XAI_P2P_MAX_PEERS_PER_PREFIX` | `"0"` | Disable prefix limits |
| `XAI_P2P_MAX_PEERS_PER_ASN` | `"0"` | Disable ASN limits |
| `XAI_P2P_MAX_PEERS_PER_COUNTRY` | `"0"` | Disable country limits |
| `XAI_P2P_MIN_UNIQUE_PREFIXES` | `"0"` | No prefix diversity required |
| `XAI_P2P_MIN_UNIQUE_ASNS` | `"0"` | No ASN diversity required |
| `XAI_P2P_MIN_UNIQUE_COUNTRIES` | `"0"` | No country diversity required |
| `XAI_P2P_MAX_UNKNOWN_GEO` | `"100"` | Allow all unknown geo peers |

## Network Information

All testnet configurations use:
- **Subnet**: 172.30.1.0/24
- **Gateway**: 172.30.1.1
- **Network name**: testnet-network

### Static IP Assignments

| Service | IP Address |
|---------|------------|
| Bootstrap | 172.30.1.10 |
| Node 1 | 172.30.1.11 |
| Node 2 | 172.30.1.12 |
| Node 3 | 172.30.1.13 |
| PostgreSQL | 172.30.1.20 |
| Redis | 172.30.1.21 |
| Explorer | 172.30.1.31 |
| Sentry 1 | 172.30.1.41 |
| Sentry 2 | 172.30.1.42 |

## Understanding Consensus Results

- **100% consensus**: All sampled intervals showed agreement (ideal, achieved on 3-node)
- **98%+ consensus**: Occasional temporary forks that self-heal (excellent for 4+ nodes)
- **90-98% consensus**: More frequent forks, may indicate timing issues
- **<90% consensus**: Investigate network or configuration issues

For reference, Ethereum PoW with 15-second blocks had a ~6-7% uncle rate. XAI achieving 98%+ consensus with ~6-second blocks is excellent performance.
