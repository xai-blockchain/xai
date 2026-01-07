# Hardware Requirements

## Minimum Requirements by Node Type

| Component | Full Node | Mining Node | Archive Node |
|-----------|-----------|-------------|--------------|
| **CPU** | 2 cores | 4 cores | 4 cores |
| **RAM** | 4 GB | 8 GB | 16 GB |
| **Storage** | 100 GB SSD | 100 GB SSD | 500 GB NVMe |
| **Network** | 25 Mbps | 50 Mbps | 50 Mbps |
| **Python** | 3.10+ | 3.10+ | 3.10+ |

## Recommended Specifications

For optimal performance on **testnet**, we recommend:

- **CPU**: 4+ cores @ 2.5 GHz or higher
- **RAM**: 8 GB minimum, 16 GB for mining
- **Storage**: 200 GB NVMe SSD (grows ~5-10 GB/month)
- **Network**: 50 Mbps symmetric bandwidth
- **OS**: Ubuntu 22.04 LTS (recommended)
- **Python**: 3.10, 3.11, or 3.12

## Cloud Provider Examples

| Provider | Instance Type | Monthly Cost | Notes |
|----------|---------------|--------------|-------|
| AWS | t3.large | ~$60 | Good for full node |
| AWS | t3.xlarge | ~$120 | Good for mining |
| Hetzner | CPX31 | ~$15 | Budget full node |
| Hetzner | CPX41 | ~$30 | Budget mining node |
| OVH | B2-15 | ~$12 | Budget option |

## Storage Growth

- Testnet: ~5-10 GB/month (estimated)
- Plan for 6+ months of growth

## Python Environment

XAI requires Python 3.10 or higher. Check your version:

```bash
python3 --version
```

Install on Ubuntu:

```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev
```

## Port Requirements

| Port | Service | Direction |
|------|---------|-----------|
| 8333 | P2P | Inbound/Outbound |
| 8545 | JSON-RPC | Outbound (or expose for public RPC) |
| 8766 | WebSocket | Outbound (or expose for public WS) |

Ensure your firewall allows inbound connections on port 8333 for P2P networking.
