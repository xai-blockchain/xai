# Multi-Chain Integration Guide

## Overview

XAI is part of a three-chain ecosystem alongside Aura and PAW:
- **EVM-compatible** architecture with coin type 22593
- **Bridge connectivity** to Cosmos chains via Axelar
- **Unified wallet** experience across all three chains

## Chain Architecture

| Chain | Type | Coin Type | Prefix | Features |
|-------|------|-----------|--------|----------|
| Aura | Cosmos SDK | 118 | `aura` | IBC, CosmWasm |
| PAW | Cosmos SDK | 118 | `paw` | IBC, DEX |
| XAI | EVM-compatible | 22593 | `xai` | AI Trading |

## XAI Unique Features

### Different Coin Type

XAI uses coin type 22593 (EVM-compatible):
- Different derivation path from Cosmos chains
- Separate key from Aura/PAW even with same mnemonic
- Compatible with EVM signing patterns

### Bridge Architecture

XAI connects to Cosmos via Axelar:

```
┌─────────────────────────────────────────┐
│           Cross-Chain Flow              │
├─────────────────────────────────────────┤
│  Aura ←──IBC──→ PAW ←──Axelar──→ XAI   │
│   ↑              ↑               ↑      │
│  Native        Native         Bridge    │
│  Cosmos        Cosmos          GMP      │
└─────────────────────────────────────────┘
```

## Unified Wallet

The shared wallet library (`wallet/shared/`) provides:
- Single mnemonic generates addresses on all chains
- XAI gets a separate key due to different coin type
- Common interface for signing and transfers

### Usage

```typescript
import { MultiChainWallet } from '@aura-ecosystem/multi-chain-wallet';

const wallet = await MultiChainWallet.fromMnemonic(mnemonic);

// XAI address uses different derivation
const xaiAccount = await wallet.getAccount('xai-mainnet-1');
// xai1... (different key from aura1.../paw1...)

// Get all accounts
const accounts = await wallet.getMainnetAccounts();
// Returns accounts for Aura, PAW, and XAI
```

### Key Derivation

| Chain | HD Path | Result |
|-------|---------|--------|
| Aura | m/44'/118'/0'/0/0 | aura1abc... |
| PAW | m/44'/118'/0'/0/0 | paw1abc... (linked) |
| XAI | m/44'/22593'/0'/0/0 | xai1xyz... (independent) |

## Ledger Support

XAI requires the Ethereum app on Ledger (not Cosmos):
- Uses coin type 22593
- Compatible with EVM signing
- Separate from Aura/PAW Ledger workflow

## Network Ports

XAI uses port range 12000-12999:

| Service | Port |
|---------|------|
| RPC | 12657 |
| REST | 12317 |
| gRPC | 12090 |

## Testing

```bash
cd wallet/shared
npm test
```

Includes XAI-specific tests:
- Address derivation with coin type 22593
- Independent key from Cosmos chains
- Chain configuration validation
