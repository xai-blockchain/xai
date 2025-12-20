---
sidebar_position: 1
---

# What is XAI?

XAI is a Python-based **AI-powered blockchain** featuring proof-of-work consensus, intelligent governance, and comprehensive wallet management. Built for security, extensibility, and developer productivity.

## Key Features

- **Proof-of-Work Consensus**: SHA-256 based mining with adjustable difficulty
- **AI Governance**: Intelligent proposal analysis and governance recommendations
- **AI Trading**: Advanced trading strategies with machine learning models
- **UTXO Model**: Bitcoin-style transaction model with full signature verification
- **Atomic Swaps**: Cross-chain trading with 11+ cryptocurrencies
- **Smart Contracts**: EVM-compatible smart contract execution
- **Mobile SDKs**: React Native and Flutter SDKs for mobile development
- **Enterprise Ready**: AML compliance tools and regulatory features

## Quick Start

Get up and running in just 5 minutes:

```bash
# Install XAI
pip install -e .

# Generate a wallet
xai-wallet generate-address

# Request testnet tokens
xai-wallet request-faucet --address YOUR_ADDRESS

# Start a node
xai-node
```

## Architecture

XAI is organized into several key modules:

- **Core Blockchain**: Block validation, mining, consensus
- **Wallet System**: Key management, multi-sig, HD wallets
- **AI Module**: Trading strategies, governance analysis
- **Network Layer**: P2P communication, peer discovery
- **Mobile SDKs**: Cross-platform mobile development

## Network Details

### Testnet
- **Network ID**: 0xABCD
- **RPC Port**: 12001
- **P2P Port**: 12002
- **Address Prefix**: TXAI
- **Block Time**: 2 minutes
- **Faucet**: 100 XAI per request

### Mainnet
- **Network ID**: 0x5841
- **RPC Port**: 8546
- **P2P Port**: 8545
- **Address Prefix**: XAI
- **Max Supply**: 121,000,000 XAI

## Getting Help

- **Documentation**: Browse the sections in the sidebar
- **GitHub**: [xai-blockchain/xai](https://github.com/xai-blockchain/xai)
- **Discord**: Join our community
- **Twitter**: [@XAIBlockchain](https://twitter.com/XAIBlockchain)

## Next Steps

- [Installation Guide](getting-started/installation) - Complete installation instructions
- [Quick Start](getting-started/quick-start) - Your first XAI transaction
- [Developer Guide](developers/overview) - Build on XAI
