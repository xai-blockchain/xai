# XAI Network Infrastructure

This document provides transparency into the infrastructure supporting the XAI blockchain network. We believe in open communication with our community about how the network is operated and secured.

## Philosophy

XAI follows blockchain community best practices for infrastructure:

- **Dedicated bare-metal servers** - No shared virtualization or cloud instances for mining/validator nodes
- **Geographic distribution** - Nodes distributed across multiple data centers and regions
- **Independent operation** - Each blockchain in our ecosystem runs on its own dedicated infrastructure
- **Transparency** - Open documentation of our infrastructure choices and security practices

## Current Testnet Infrastructure

### Primary Node

| Specification | Details |
|--------------|---------|
| **Server Type** | Dedicated bare-metal server |
| **Provider** | OVH (SoYouStart) |
| **Location** | Beauharnois, Quebec, Canada (BHS) |
| **CPU** | Intel Xeon E3-1270 v6 @ 3.80GHz (4 cores / 8 threads) |
| **Memory** | 64 GB DDR4 ECC |
| **Storage** | 2x 480GB SSD (RAID 1) |
| **Network** | 500 Mbps dedicated bandwidth |
| **IPv4** | Dedicated static IP |

### Why Bare-Metal?

We chose dedicated bare-metal servers over cloud instances for several reasons:

1. **Predictable Performance** - No noisy neighbor issues or resource contention
2. **Security** - Full control over the hardware stack with no hypervisor layer
3. **Cost Efficiency** - Better price-to-performance for long-running blockchain nodes
4. **Community Trust** - Bare-metal is the accepted standard for serious blockchain infrastructure

### Network Architecture

```
                    ┌─────────────────┐
                    │   Cloudflare    │
                    │   (DDoS/CDN)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     Nginx       │
                    │  (Reverse Proxy)│
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│  API (8545)   │   │    Explorer   │   │    Faucet     │
└───────────────┘   └───────────────┘   └───────────────┘
```

### Public Endpoints

| Service | URL | Port |
|---------|-----|------|
| JSON-RPC API | https://testnet-rpc.xaiblockchain.com | 443 |
| Explorer | https://testnet-explorer.xaiblockchain.com | 443 |
| Faucet | https://testnet-faucet.xaiblockchain.com | 443 |
| Monitoring | https://monitoring.xaiblockchain.com | 443 |
| Snapshots | https://snapshots.xaiblockchain.com | 443 |

### Security Measures

- **Firewall** - UFW with strict ingress rules; only required ports exposed
- **SSH** - Key-based authentication only, no password login
- **TLS** - All public endpoints secured with Let's Encrypt certificates
- **Updates** - Automated security updates via unattended-upgrades
- **Monitoring** - 24/7 monitoring via Grafana with alerting

## XAI-Specific Infrastructure

### Proof-of-Work Mining

XAI uses SHA-256 proof-of-work consensus. Our infrastructure supports:

| Component | Details |
|-----------|---------|
| **Algorithm** | SHA-256 (Bitcoin-compatible) |
| **Block Time** | ~2 minutes target |
| **Difficulty** | Dynamic adjustment |
| **Max Supply** | 121,000,000 XAI |

### Atomic Swap Infrastructure

XAI supports atomic swaps with 11+ cryptocurrencies. Our infrastructure includes:

- **HTLC Servers** - Hash Time-Locked Contract coordination
- **Multi-chain Watchers** - Monitor partner chain transactions
- **Liquidity Pools** - Reserved funds for swap execution

### Supported Swap Partners

| Chain | Status |
|-------|--------|
| Bitcoin (BTC) | Active |
| Ethereum (ETH) | Active |
| Litecoin (LTC) | Active |
| Bitcoin Cash (BCH) | Active |
| Dogecoin (DOGE) | Active |
| Monero (XMR) | Active |
| Zcash (ZEC) | Active |
| Dash (DASH) | Active |
| Stellar (XLM) | Active |
| Ripple (XRP) | Active |
| Cardano (ADA) | Active |

### AI Governance Infrastructure

The AI-powered governance system requires additional infrastructure:

- **AI Model Servers** - Local inference for proposal analysis
- **Recommendation Engine** - Voting suggestions based on proposal content
- **Governance Dashboard** - Real-time proposal tracking

## Mainnet Plans

For mainnet launch, we plan to expand infrastructure with:

- **Multiple seed nodes** across different geographic regions (NA, EU, Asia)
- **Mining pool support** for community miners
- **Multiple hosting providers** to avoid single provider dependency
- **Dedicated atomic swap relayers** for cross-chain liquidity
- **Independent snapshot providers** for quick node bootstrapping

## Running Your Own Node

We encourage community members to run their own nodes and miners. See our documentation:

- [Quick Start Guide](docs/QUICK_START.md)
- [CLI Guide](docs/CLI_GUIDE.md)
- [RPC Documentation](docs/rpc.md)

### Minimum Requirements for Nodes

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| Memory | 4 GB | 8+ GB |
| Storage | 100 GB SSD | 500 GB SSD |
| Network | 50 Mbps | 100+ Mbps |
| Python | 3.10+ | 3.11+ |

### Mining Hardware Recommendations

| Setup | Hardware | Expected Hashrate |
|-------|----------|-------------------|
| Hobbyist | Modern CPU | 10-50 MH/s |
| Enthusiast | ASIC (SHA-256) | 10-100 TH/s |
| Professional | ASIC Farm | 1+ PH/s |

*Note: GPU mining is not efficient for SHA-256. CPU mining is supported for testnet participation.*

## Contact

For infrastructure-related inquiries:
- Email: info@xaiblockchain.com
- Discord: [Join our community](https://discord.gg/xai)
- GitHub: [xai-blockchain/xai](https://github.com/xai-blockchain/xai)

## Changelog

| Date | Change |
|------|--------|
| 2025-01-01 | Initial testnet infrastructure deployed |

---

*Last updated: January 2025*
