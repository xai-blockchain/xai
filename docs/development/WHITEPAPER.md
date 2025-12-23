# XAI Blockchain Whitepaper (Technical Draft)

Version: 0.2.x
Status: Development

1. Introduction

XAI is a Python-based blockchain implementing a proof-of-work (PoW) chain with a UTXO transaction model, Merkle proofs, and a modular node exposing a REST API. The project targets clarity and auditability with a focus on correctness, validation, and security middleware. This whitepaper reflects the current codebase.

2. Design Goals

- Simplicity first: readable reference implementation
- Security by default: validation, nonces, signature checks, structured logging
- Extensibility: modular components for consensus, networking, governance
- Operability: metrics, basic explorer, configuration manager

3. Architecture Overview

- Node (Flask-based): API endpoints, CORS policies, request validation, P2P hooks
- Blockchain Core: UTXO transactions, blocks, PoW, Merkle proofs, difficulty setting
- Wallet CLI: key generation, balance query, send, import/export, faucet helper
- Governance: proposal management, vote locking, quadratic voting primitives
- Light Client: block header tracking and inclusion proof verification
- Monitoring & Security: structured metrics, security event routing, webhook forwarder

4. Consensus and Blocks

- Algorithm: PoW (SHA-256), `Block.mine_block()` finds hashes with leading zeros per difficulty
- Difficulty: configurable integer, target prefix of zeros
- Block contents: index, timestamp, transactions, previous hash, Merkle root, nonce, difficulty
- Coinbase: first transaction rewards miner address (configurable reward schedule)

5. Monetary Policy

Defined in `xai.core.blockchain.Blockchain`:
- Initial block reward: 12 XAI
- Halving interval: 262,800 blocks
- Maximum supply: 121,000,000 XAI
- Transaction fee: percentage applied to fees (currently 0.24%)

6. Transactions (UTXO)

- Fields: sender, recipient, amount, fee, timestamp, signature, public key, nonce, inputs, outputs
- Signatures: ECDSA over transaction hash; address derived from pubkey hash (XAI prefix)
- Replace-By-Fee (RBF): optional `rbf_enabled` and `replaces_txid`
- Size/fee rate estimation used for prioritization
- Merkle proofs used for inclusion verification

7. Validation

- Nonce tracking (`NonceTracker`) for replay protection
- `TransactionValidator` enforces signature validity, balance/UTXO checks, and schema validation
- Chain validation utilities with checkpointing

8. Governance Primitives

- Proposal lifecycle (`ProposalManager`) with minimum stake and quorum
- Vote locking (`VoteLocker`) with time-weighted voting
- Quadratic voting support (`QuadraticVoter`) and identity hooks

9. Networking and Node Services

- REST API served via Flask in `xai.core.node`
- CORS policies via `CORSPolicyManager`; request size limits and validation middleware
- P2P manager skeleton for peer discovery and block/tx propagation
- Security sink and optional webhook forwarder for critical events

10. Wallets and Tooling

- CLI (`xai.wallet.cli`): generate address, balance, send, import/export, faucet request
- AES-GCM encryption for exported wallets; HMAC for integrity

11. Explorer

- Simple explorer (`xai.block_explorer`/`xai.explorer`) for blocks, transactions, dashboard
- Caching and formatting helpers

12. Configuration and Storage

- `ConfigManager` loads layered configuration (file, env, CLI overrides)
- `BlockchainStorage` persists blocks and UTXO state under a data directory (not tracked in repo)

13. Security and Monitoring

- Structured logging and metrics
- Security validation, input schemas, and event routing with optional webhook delivery

14. Future Work

- Robust P2P protocol and consensus messages
- Difficulty adjustment algorithm refinements
- Smart contract VM expansion and audited standard library
- Full testnet deployment guide with hardened defaults

15. References

- SHA-256, ECDSA, UTXO model literature
- Project documentation under `docs/`

Disclaimer

This document describes the current implementation state. XAI is under active development and not intended for production use without further auditing and hardening.
|--------|--------|------------------|--------------|
| 1 | 0 - 262,799 | 12 XAI | 3,153,600 |
| 2 | 262,800 - 525,599 | 6 XAI | 1,576,800 |
| 3 | 525,600 - 788,399 | 3 XAI | 788,400 |
| 4 | 788,400 - 1,051,199 | 1.5 XAI | 394,200 |
| ... | ... | ... | ... |

### 4.3 Genesis Distribution

The genesis block includes a premine allocation for development, early adopters, and ecosystem funding. The exact distribution is defined in the genesis file and verified via SHA-256 hash matching.

### 4.4 Transaction Fees

Users pay transaction fees to miners. Fee market operates through:
- Minimum fee thresholds
- Priority ordering in mempool based on fee per byte
- Fee burning option (removes coins from circulation)

## 5. Transaction Model

### 5.1 UTXO System

XAI uses an Unspent Transaction Output (UTXO) model similar to Bitcoin. Each transaction consumes existing UTXOs and creates new ones.

**Transaction Structure**:
```
{
  "sender": address,
  "recipient": address,
  "amount": decimal,
  "fee": decimal,
  "timestamp": unix_timestamp,
  "signature": cryptographic_signature,
  "tx_type": transaction_type
}
```

### 5.2 Transaction Types

- **Standard**: Basic value transfer
- **Multi-signature**: Requires multiple signatures
- **Time Capsule**: Locked until specified timestamp
- **Smart Contract**: Contract creation or execution
- **Atomic Swap**: Cross-chain exchange
- **Governance**: Proposal or vote
- **Token Burn**: Permanent supply reduction

### 5.3 Multi-Signature Transactions

Support for m-of-n multi-signature wallets where m signatures are required from n authorized parties. Common configurations:
- 2-of-3: Shared control with backup key
- 3-of-5: Corporate treasury management
- Custom: User-defined thresholds

## 6. Smart Contracts

### 6.1 Contract System

Smart contracts are programs that execute on the blockchain. The system provides:
- Deterministic execution environment
- Gas-based resource metering
- State persistence
- Event emission
- Inter-contract calls

### 6.2 Contract Deployment

Contracts are deployed via special transactions that include:
- Bytecode of the contract
- Constructor parameters
- Initial funding
- Gas limit for deployment

### 6.3 Execution Model

Contracts execute in a sandboxed virtual machine with:
- Stack-based architecture
- Limited instruction set
- Gas consumption per operation
- State read/write capabilities
- Access to transaction context

## 7. Atomic Swaps

### 7.1 Cross-Chain Trading

XAI supports atomic swaps with 11 cryptocurrencies, enabling trustless cross-chain exchanges without intermediaries.

**Supported Assets**:
- Bitcoin (BTC)
- Ethereum (ETH)
- Litecoin (LTC)
- Bitcoin Cash (BCH)
- Dogecoin (DOGE)
- Monero (XMR)
- Zcash (ZEC)
- Dash (DASH)
- Stellar (XLM)
- Ripple (XRP)
- Cardano (ADA)

### 7.2 Swap Protocol

Atomic swaps use Hash Time-Locked Contracts (HTLCs):

1. Initiator creates HTLC on XAI chain with hash lock
2. Participant creates HTLC on counterparty chain with same hash
3. Initiator reveals preimage and claims counterparty coins
4. Participant uses revealed preimage to claim XAI coins
5. If timeout expires, both parties reclaim their funds

### 7.3 Implementation

```
XAI Chain:              Counterparty Chain:
┌──────────┐           ┌──────────┐
│ Lock XAI │────┐      │          │
│ Hash: H  │    │      │          │
│ Timeout: │    │      │          │
│ T1       │    │      │          │
└──────────┘    │      └──────────┘
                │
                ▼
          Create matching HTLC
                │
                ▼
┌──────────┐           ┌──────────┐
│          │           │ Lock BTC │
│          │           │ Hash: H  │
│          │      ┌────│ Timeout: │
│          │      │    │ T2       │
└──────────┘      │    └──────────┘
                  ▼
            Reveal preimage
                  │
                  ▼
┌──────────┐           ┌──────────┐
│ Claim    │           │ Claim    │
│ BTC      │           │ XAI      │
└──────────┘           └──────────┘
```

## 8. AI Governance System

### 8.1 Overview

The AI governance system analyzes proposals and provides structured feedback. Human participants retain final decision authority through voting.

### 8.2 Proposal Lifecycle

1. **Submission**: Community member submits proposal
2. **AI Analysis**: System analyzes technical feasibility, security implications, and community impact
3. **Discussion Period**: Community reviews proposal and AI analysis
4. **Voting**: Token holders vote on proposal
5. **Implementation**: Approved proposals are scheduled for implementation

### 8.3 AI Analysis Components

The AI system evaluates:
- **Technical Feasibility**: Can the proposal be implemented safely?
- **Security Impact**: Does it introduce vulnerabilities?
- **Economic Effects**: How does it affect tokenomics?
- **Community Alignment**: Does it match stated project goals?
- **Implementation Complexity**: What resources are required?

### 8.4 Safety Controls

AI governance includes:
- Human override capability
- Proposal rejection threshold
- Analysis transparency (all reasoning published)
- Voting weight verification
- Execution delay for safety review

### 8.5 Voting Mechanism

- Vote weight proportional to held XAI
- Minimum participation threshold
- Time-locked voting period
- On-chain vote recording
- Result verification by all nodes

## 9. Time Capsules

### 9.1 Concept

Time capsules allow users to lock coins until a specified future timestamp. Locked coins cannot be spent until the unlock time.

### 9.2 Implementation

```
{
  "type": "time_capsule",
  "amount": locked_amount,
  "recipient": destination_address,
  "unlock_time": unix_timestamp,
  "creator": sender_address
}
```

### 9.3 Use Cases

- Savings mechanism
- Inheritance planning
- Vesting schedules
- Scheduled payments
- Trust fund implementation

### 9.4 Security

- Cryptographic lock prevents early withdrawal
- Network consensus enforces unlock time
- Creator cannot reverse after creation
- Funds remain in verified UTXO set

## 10. Wallet System

### 10.1 Wallet Types

**Standard Wallet**:
- Single private key control
- HD derivation support
- Address generation
- Transaction signing

**Multi-Signature Wallet**:
- Shared control between multiple parties
- Configurable signature threshold
- Key rotation capability
- Recovery mechanisms

**Hardware Wallet** (Roadmap):
- Ledger device integration
- Offline key storage
- Transaction verification on device

**Embedded Wallet** (Roadmap):
- Application-integrated wallets
- Account abstraction
- Social recovery

### 10.2 Address Format

- **Testnet**: TXAI prefix + base58 encoded public key hash
- **Mainnet**: XAI prefix + base58 encoded public key hash

### 10.3 Key Management

- BIP32/BIP44 HD wallet derivation
- Secure key storage with encryption
- Mnemonic phrase backup (BIP39)
- Optional password protection

## 11. Compliance and AML

### 11.1 Transaction Monitoring

Built-in monitoring assigns risk scores to transactions based on:
- Transaction amount
- Pattern detection (structuring, rapid succession)
- Velocity analysis
- Address reputation

### 11.2 Risk Scoring

Transactions receive scores from 0-100:
- **0-30**: Low risk
- **31-60**: Medium risk
- **61-80**: High risk
- **81-100**: Critical risk

### 11.3 Reporting Capabilities

System provides:
- `/regulator/flagged`: List of flagged transactions
- `/history/<address>`: Transaction history with metadata
- Audit trail generation
- Compliance report export

### 11.4 Address Monitoring

- Blacklist/sanctions list support
- Flagged address tracking
- Source of funds analysis
- Governance-based list updates

## 12. Network Protocol

### 12.1 Peer Discovery

Nodes discover peers through:
- Bootstrap node list
- Peer exchange protocol
- DNS seeds
- Manual peer addition

### 12.2 Message Types

- `block`: New block broadcast
- `transaction`: New transaction broadcast
- `get_blocks`: Request block data
- `get_peers`: Request peer list
- `version`: Protocol version handshake
- `ping/pong`: Connection keepalive

### 12.3 Synchronization

New nodes synchronize via:
1. Request block headers from peers
2. Validate header chain
3. Request full blocks
4. Validate transactions
5. Build UTXO set
6. Verify chain state

## 13. Security Features

### 13.1 Attack Resistance

**51% Attack**: Proof-of-work makes history rewriting computationally expensive

**Double Spend**: UTXO validation and confirmation requirements prevent double spending

**Sybil Attack**: Proof-of-work provides sybil resistance

**Eclipse Attack**: Diverse peer connections and peer exchange

### 13.2 Validation

Multiple validation layers:
- Transaction signature verification
- UTXO existence verification
- Double-spend detection
- Balance verification
- Fee validation
- Block structure verification
- Consensus rule enforcement

### 13.3 Rate Limiting

API endpoints include:
- Request rate limits (120 requests per minute default)
- JSON payload size limits (1MB default)
- Connection limits per IP
- Transaction flooding prevention

## 14. Storage Architecture

### 14.1 Directory-Based Storage

Version 0.2.0 introduced directory-based blockchain storage for improved performance:

```
data/
├── blocks/
│   ├── 00000/
│   │   ├── block_00000.json
│   │   ├── block_00001.json
│   │   └── ...
│   └── 00001/
└── index/
    ├── height_index.json
    └── tx_index.json
```

### 14.2 Benefits

- Faster block retrieval
- Reduced memory footprint
- Parallel processing capability
- Simplified pruning
- Better file system performance

### 14.3 Indexing

System maintains indices for:
- Block height to file mapping
- Transaction ID to block mapping
- Address to transaction mapping
- UTXO set state

## 15. Roadmap Items

### 15.1 Light Client

Planned implementation of SPV (Simplified Payment Verification) clients:
- Header-only sync
- Merkle proof verification
- Reduced storage requirements
- Mobile device compatibility

### 15.2 Mobile Bridge

QR code-based interface for mobile wallet integration:
- Transaction signing requests
- Address display
- Balance queries
- Payment protocol support

### 15.3 Fiat On-Ramps

Payment card integration (locked until November 2026):
- Stripe/payment processor integration
- KYC workflow
- Purchase flow
- Compliance tooling

**Governance Unlock**: Between March 12, 2026 and November 1, 2026, a governance vote requiring 5 votes with 66% support can unlock fiat rails early.

### 15.4 Additional Features

- Micro-AI assistant network
- Mini-app framework for polls/votes/games
- Enhanced block explorer
- Performance optimizations
- Additional atomic swap pairs

## 16. Technical Specifications Summary

| Parameter | Value |
|-----------|-------|
| Consensus | Proof of Work (SHA-256) |
| Max Supply | 121,000,000 XAI |
| Block Time | 120 seconds |
| Initial Reward | 12 XAI |
| Halving Interval | 262,800 blocks (~1 year) |
| Mainnet Port | 8545 |
| Testnet Port | 18545 |
| Address Prefix (Mainnet) | XAI |
| Address Prefix (Testnet) | TXAI |
| Network ID (Mainnet) | 0x5841 |
| Network ID (Testnet) | 0xABCD |

## 17. Development Status

**Version 0.2.0** includes:
- Core blockchain implementation
- Directory-based storage
- Proof-of-work consensus
- Transaction validation
- Wallet management
- AI governance framework
- Atomic swap support
- Smart contracts
- Time capsules
- Multi-signature wallets
- AML compliance tools
- Block explorer
- Electron desktop wallet

**Current Focus**:
- Multi-node network testing
- Security audits
- Performance optimization
- Documentation completion

## 18. References

### 18.1 Source Code

- Repository: provided by your organization
- License: MIT
- Documentation: docs/README.md

### 18.2 Standards

- BIP32: HD Wallet derivation
- BIP39: Mnemonic phrases
- BIP44: Multi-account hierarchy
- SHA-256: Hash function
- ECDSA: Signature algorithm

## 19. Disclaimer

XAI is experimental software under active development. The network is provided as-is without warranties. Users should understand cryptocurrency risks before participating. This whitepaper describes technical implementation and does not constitute financial advice or investment guidance.

---

**Document Version**: 0.2.0
**Last Updated**: December 2025

---

## Contact

- Website: https://xaiblockchain.com
- GitHub: https://github.com/xai-blockchain
- Discord: https://discord.gg/xai-blockchain
- Twitter: @xaiblockchain
- Email: contact@xaiblockchain.com

---

## Other Projects

XAI is part of a suite of blockchain projects designed for the decentralized future:

- **AURA** — Privacy-preserving identity verification with zero-PII architecture. [useyouraura.com](https://useyouraura.com)
- **PAW Network** — Verifiable AI compute coordination with native DEX and oracle. [poaiwblockchain.com](https://poaiwblockchain.com)

*Building the decentralized future, together.*
