# XAI Port Reference

This document defines the canonical port assignments for the XAI blockchain project.

All XAI services use ports in the **12000-12999** range to avoid conflicts with other projects (Aura: 10000-10999, PAW: 11000-11999).

## Core Node Ports

### Node 1 (Primary)
- **RPC/API**: 12001 - JSON-RPC endpoint for API access
- **P2P**: 12002 - Peer-to-peer networking
- **WebSocket**: 12003 - WebSocket connections

### Node 2 (Secondary)
- **RPC/API**: 12011 - JSON-RPC endpoint
- **P2P**: 12012 - Peer-to-peer networking
- **WebSocket**: 12013 - WebSocket connections

### Node 3 (Tertiary)
- **RPC/API**: 12021 - JSON-RPC endpoint
- **P2P**: 12022 - Peer-to-peer networking
- **WebSocket**: 12023 - WebSocket connections

### Node 4 (Quaternary)
- **RPC/API**: 12031 - JSON-RPC endpoint
- **P2P**: 12032 - Peer-to-peer networking
- **WebSocket**: 12033 - WebSocket connections

## Infrastructure Services

### Monitoring
- **Prometheus**: 12090 - Metrics collection and storage
- **Grafana**: 12030 - Dashboard and visualization UI

### Explorer
- **Block Explorer**: 12080 - Web interface for blockchain exploration
- **Explorer Backend API**: 12081 - REST API for explorer data

### Application Services
- **Flask API**: 12050 - Primary application API server
- **Flask Debug**: 12051 - Debug/development API server

### Testing & Development
- **Toxiproxy API**: 12800 - Chaos engineering proxy control
- **Toxiproxy RPC Proxies**: 12101-12110 - RPC endpoint proxies
- **Toxiproxy WS Proxies**: 12111-12120 - WebSocket proxies
- **Toxiproxy P2P Proxies**: 12121-12130 - P2P connection proxies

## Quick Reference Table

| Service | Port | URL |
|---------|------|-----|
| Node API (Primary) | 12001 | http://localhost:12001 |
| Node P2P | 12002 | tcp://localhost:12002 |
| Node WebSocket | 12003 | ws://localhost:12003 |
| Grafana Dashboard | 12030 | http://localhost:12030 |
| Flask API | 12050 | http://localhost:12050 |
| Block Explorer | 12080 | http://localhost:12080 |
| Prometheus | 12090 | http://localhost:12090 |
| Toxiproxy Control | 12800 | http://localhost:12800 |

## Environment Variable Configuration

Use these environment variables to configure ports:

```bash
# Core node ports
XAI_RPC_PORT=12001
XAI_P2P_PORT=12002
XAI_WS_PORT=12003

# Monitoring
XAI_PROMETHEUS_PORT=12090
XAI_GRAFANA_PORT=12030

# Services
XAI_EXPLORER_PORT=12080
XAI_FLASK_PORT=12050
```

## Docker Compose Port Mappings

Standard Docker Compose port mappings:

```yaml
services:
  xai-node-1:
    ports:
      - "12001:8545"  # RPC (internal 8545 -> external 12001)
      - "12002:30303" # P2P
      - "12003:8546"  # WebSocket

  grafana:
    ports:
      - "12030:3000"  # Grafana UI

  prometheus:
    ports:
      - "12090:9090"  # Prometheus

  explorer:
    ports:
      - "12080:8000"  # Block explorer

  flask-api:
    ports:
      - "12050:5000"  # Flask API
```

## Legacy Ports (Deprecated)

The following ports were previously used and should be updated:

- ~~5000~~ → 12001 (Node API)
- ~~3000~~ → 12080 (Block Explorer)
- ~~8545~~ → 12001 (RPC)
- ~~8546~~ → 12003 (WebSocket)
- ~~18545~~ → 12001 (Testnet RPC)
- ~~18546~~ → 12003 (Testnet WebSocket)

## Notes

1. **Internal vs External Ports**: Docker containers may use standard internal ports (8545, 5000, etc.) but these are mapped to the 12000-12999 range externally.

2. **Mainnet vs Testnet**: Both mainnet and testnet use the same port range. The network type is determined by the `XAI_NETWORK` environment variable, not by port numbers.

3. **Port Conflicts**: Before starting services, ensure no other applications are using ports in the 12000-12999 range:
   ```bash
   netstat -tuln | grep "120[0-9][0-9]"
   ```

4. **Firewall Configuration**: For production deployments, ensure appropriate firewall rules allow:
   - RPC/API port (12001) - for API access
   - P2P port (12002) - for peer connections
   - Explorer port (12080) - for public access (if desired)

5. **Load Balancing**: For high-availability setups, use load balancers in front of multiple node instances, all using their designated ports from this range.

## See Also

- [XAI Configuration Guide](../CLAUDE.md)
- [Port Allocation Scheme](../../PORT_ALLOCATION.md)
- [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)
- [Docker Setup](../docker/README.md)
