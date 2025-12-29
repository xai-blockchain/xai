# Getting Started with XAI Blockchain

Welcome to XAI - a Python-based Proof-of-Work blockchain with AI governance and atomic swaps.

## Quick Links

- **[QUICKSTART Guide](QUICKSTART.md)** - Install and run in 5 minutes
- **[Testnet Guide](user-guides/TESTNET_GUIDE.md)** - Join the testnet
- **[API Reference](api/rest-api.md)** - Build applications

## What is XAI?

XAI is a production-ready blockchain featuring:
- **Proof-of-Work Consensus** - SHA-256 with dynamic difficulty
- **UTXO Transaction Model** - Bitcoin-style transaction outputs
- **AI Governance** - Intelligent proposal evaluation
- **Atomic Swaps** - Cross-chain trading (11+ cryptocurrencies)
- **Smart Contracts** - EVM-compatible execution

## Architecture

```
Application Layer: Wallet CLI, Explorer, DApps, SDKs
Service Layer:     REST API, WebSocket, RPC
Core Layer:        Blockchain, Consensus, Mempool, P2P
Storage Layer:     Block DB, State DB, UTXO Set
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| **UTXO** | Unspent Transaction Output - tracks spendable coins |
| **Block** | Container of transactions, mined via PoW |
| **Merkle Tree** | Binary hash tree for efficient verification |
| **SPV** | Simplified Payment Verification for light clients |

## Network Parameters

| Parameter | Testnet | Mainnet |
|-----------|---------|---------|
| Address Prefix | TXAI | XAI |
| P2P / RPC Ports | 18545 / 18546 | 8545 / 8546 |
| Block Time | 2 min | 2 min |
| Max Supply | 121M | 121M |

## Quick Install

```bash
git clone https://github.com/xai-blockchain/xai.git && cd xai
pip install -c constraints.txt -e ".[dev]"
python -m xai.core.node
```

See **[QUICKSTART.md](QUICKSTART.md)** for detailed options.

## Next Steps

**Users:** [QUICKSTART](QUICKSTART.md) | [Wallet Setup](user-guides/wallet-setup.md) | [Mining](user-guides/mining.md)

**Developers:** [Local Setup](development/local-setup.md) | [SDK](api/sdk.md) | [REST API](api/rest-api.md)

**Operators:** [Testnet](deployment/testnet.md) | [Production](deployment/production.md) | [Monitoring](deployment/monitoring.md)

## Resources

- [Whitepaper](development/WHITEPAPER.md) - Technical specification
- [Architecture](architecture/overview.md) - System design
- [FAQ](user-guides/faq.md) - Common questions

---

*Version 0.2.0 | [GitHub](https://github.com/xai-blockchain/xai)*
