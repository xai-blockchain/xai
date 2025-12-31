# XAI Blockchain Protocol Specification

**Version:** 1.0.0
**Status:** Production
**Last Updated:** 2025-12-30

## 1. Overview

XAI is a proof-of-work blockchain with EVM compatibility, designed for AI-enhanced decentralized applications.

## 2. Consensus Mechanism

### 2.1 Proof of Work (PoW)
- **Algorithm:** SHA3-256 (Keccak)
- **Block Time Target:** 60 seconds
- **Difficulty Adjustment:** Every 10 blocks using LWMA (Linearly Weighted Moving Average)

### 2.2 Block Structure
```
Block:
  - index: uint64
  - timestamp: uint64 (Unix epoch)
  - previous_hash: bytes32
  - merkle_root: bytes32
  - nonce: uint64
  - difficulty: uint256
  - transactions: Transaction[]
```

### 2.3 Finality
- **Checkpoint Finality:** Blocks become final after 100 confirmations
- **Validator Finality:** BFT-style finality with 2/3 validator attestations

## 3. Transaction Format

### 3.1 Base Transaction
```
Transaction:
  - chain_context: bytes32 (replay protection)
  - sender: address (20 bytes)
  - recipient: address (20 bytes)
  - amount: uint256
  - fee: uint256
  - nonce: uint64
  - timestamp: uint64
  - signature: bytes65 (ECDSA secp256k1, canonical low-S)
```

### 3.2 Signature Scheme
- **Curve:** secp256k1
- **Format:** ECDSA with deterministic k (RFC 6979)
- **Malleability Protection:** BIP-62 canonical low-S enforcement

## 4. Address Format

### 4.1 Generation
1. Generate private key (256-bit from CSPRNG)
2. Derive public key (secp256k1 uncompressed)
3. Hash public key (SHA3-256)
4. Take last 20 bytes
5. Add checksum (EIP-55 style)

### 4.2 Format
- Prefix: `0x`
- Length: 40 hex characters (20 bytes)
- Checksum: Mixed-case encoding

## 5. Network Protocol

### 5.1 P2P Layer
- **Transport:** WebSocket with TLS 1.3
- **Discovery:** DHT-based peer discovery
- **Message Format:** JSON-RPC 2.0

### 5.2 Message Types
| Type | Description |
|------|-------------|
| `block` | New block announcement |
| `tx` | New transaction announcement |
| `getblocks` | Request block range |
| `gettx` | Request transaction |
| `checkpoint` | Checkpoint announcement |
| `ping/pong` | Keepalive |

## 6. Smart Contracts

### 6.1 EVM Compatibility
- **Version:** Shanghai-compatible
- **Gas Model:** EIP-1559 base fee + priority fee
- **Limits:** 24KB max contract size (EIP-170)

### 6.2 Precompiles
| Address | Function |
|---------|----------|
| 0x01 | ecRecover |
| 0x02 | SHA256 |
| 0x03 | RIPEMD160 |
| 0x04 | identity |
| 0x05 | modexp |
| 0x06-0x08 | BN256 curve ops |
| 0x09 | BLAKE2F |

## 7. Token Economics

### 7.1 Supply
- **Maximum Supply:** 121,000,000 XAI
- **Initial Distribution:** Genesis block allocation
- **Emission:** Block rewards (halving every 4 years)

### 7.2 Block Rewards
| Era | Reward |
|-----|--------|
| 1 (blocks 0-2,100,000) | 50 XAI |
| 2 (blocks 2,100,001-4,200,000) | 25 XAI |
| 3+ | Continues halving |

## 8. Security Invariants

### 8.1 Consensus
- Chain with most cumulative work is canonical
- Blocks must reference valid previous block
- Maximum reorg depth: 100 blocks

### 8.2 Transactions
- Nonces must be sequential per address
- Signatures must be valid and canonical
- Balances must be sufficient for amount + fee

### 8.3 State
- UTXO set must be consistent with chain
- No double-spending within or across blocks
- Merkle root must match transactions

## 9. Upgrade Mechanism

### 9.1 Soft Forks
- Backward-compatible rule tightening
- Activated by miner signaling (95% threshold)

### 9.2 Hard Forks
- Require node upgrade
- Announced 6 months in advance
- Coordinated block height activation

## 10. References

- [Bitcoin Whitepaper](https://bitcoin.org/bitcoin.pdf)
- [Ethereum Yellow Paper](https://ethereum.github.io/yellowpaper/)
- [BIP-62: Dealing with Malleability](https://github.com/bitcoin/bips/blob/master/bip-0062.mediawiki)
- [EIP-155: Replay Attack Protection](https://eips.ethereum.org/EIPS/eip-155)
- [EIP-1559: Fee Market](https://eips.ethereum.org/EIPS/eip-1559)
