# XAI Blockchain Technical Documentation

Comprehensive technical reference for the XAI blockchain implementation.

---

## System Architecture

### Core Components

```
XAI Blockchain Architecture
├── Consensus Layer (Proof-of-Work)
│   ├── Mining Algorithm (SHA-256)
│   ├── Difficulty Adjustment
│   └── Block Validation
├── Transaction Layer (UTXO Model)
│   ├── Transaction Pool (Mempool)
│   ├── UTXO Manager
│   └── Transaction Validator
├── Network Layer
│   ├── P2P Protocol
│   ├── Peer Discovery
│   └── Block Propagation
├── Storage Layer
│   ├── Blockchain Storage
│   ├── UTXO Set
│   └── State Database
├── API Layer
│   ├── REST API (Flask)
│   ├── WebSocket API
│   └── RPC Interface
└── Application Layer
    ├── Wallet Management
    ├── Smart Contracts (EVM)
    ├── Atomic Swaps
    └── AI Governance
```

---

## Consensus Mechanism

### Proof-of-Work (SHA-256)

**Algorithm**: Bitcoin-style SHA-256 proof-of-work

**Block Mining**:
```python
def mine_block(transactions, previous_hash, difficulty):
    nonce = 0
    target = "0" * difficulty
    while True:
        block_hash = sha256(block_data + str(nonce))
        if block_hash.startswith(target):
            return Block(nonce, block_hash)
        nonce += 1
```

**Difficulty Adjustment**:
- Adjusts every 2016 blocks
- Target block time: 2 minutes
- Difficulty increases/decreases to maintain target

**Block Reward Schedule**:
- Initial reward: 50 XAI
- Halving interval: 210,000 blocks
- Maximum supply: 121,000,000 XAI

---

## Transaction Model

### UTXO (Unspent Transaction Output)

**Transaction Structure**:
```python
{
    "txid": "0xabc123...",
    "sender": "XAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "recipient": "XAI1recipient...",
    "amount": 10.5,
    "fee": 0.001,
    "timestamp": 1704067200,
    "signature": "304402...",
    "public_key": "04abc...",
    "nonce": 42,
    "inputs": [...],
    "outputs": [...],
    "rbf_enabled": false
}
```

**Transaction Lifecycle**:
1. Client creates and signs transaction
2. Transaction submitted to mempool
3. Miner includes in block candidate
4. Block mined and propagated
5. Transaction confirmed (6 blocks recommended)

**Replace-By-Fee (RBF)**:
- Optional field `rbf_enabled`
- Allows fee bumping for stuck transactions
- Must reference original `replaces_txid`

---

## Cryptography

### Algorithms Used

**Hashing**: SHA-256 (blocks, transactions, addresses)
**Signatures**: ECDSA with secp256k1 curve
**Key Derivation**: BIP-32 (HD wallets), BIP-39 (mnemonic)
**Encryption**: AES-256-GCM (wallet export)

### Address Format

**Mainnet**: `XAI + Base58(RIPEMD160(SHA256(pubkey)))`
**Testnet**: `TXAI + Base58(RIPEMD160(SHA256(pubkey)))`

Example: `XAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`

---

## Network Protocol

### P2P Communication

**Ports**:
- Testnet P2P: 18545
- Mainnet P2P: 8545
- RPC: 18546 (testnet), 8546 (mainnet)

**Message Types**:
- `VERSION` - Handshake and version negotiation
- `GETBLOCKS` - Request block hashes
- `BLOCK` - Block propagation
- `TX` - Transaction broadcast
- `PING/PONG` - Keep-alive

**Peer Discovery**:
- DNS seeds
- Hardcoded seed nodes
- Peer exchange protocol

---

## Storage

### Data Directory Structure

```
~/.xai/
├── blocks/           # Block data
├── chainstate/       # UTXO set
├── wallet.dat        # Encrypted wallet
├── peers.dat         # Known peers
└── config.yaml       # Node configuration
```

**Database**: LevelDB for blockchain state
**Persistence**: Blocks stored as JSON (development) or binary (production)

---

## API Endpoints

### REST API

**Base URL**: `http://localhost:12001`

**Core Endpoints**:
- `GET /blockchain/stats` - Blockchain statistics
- `GET /block/{number}` - Get block by number
- `GET /transaction/{txid}` - Get transaction details
- `GET /account/{address}` - Get account balance
- `POST /send` - Broadcast transaction
- `GET /mempool` - View pending transactions

**Wallet Endpoints**:
- `POST /wallet/generate` - Generate new address
- `GET /wallet/balance` - Check balance
- `POST /wallet/sign` - Sign transaction

See `docs/api/` for complete API documentation.

---

## Smart Contracts

### EVM Compatibility

**Features**:
- Solidity contract deployment
- EVM opcode interpreter
- Gas metering
- State management

**Contract Deployment**:
```bash
# Deploy contract
curl -X POST http://localhost:12001/contract/deploy \
  -d '{"bytecode": "0x60606040...", "abi": [...]}'

# Call contract
curl -X POST http://localhost:12001/contract/call \
  -d '{"address": "0x123...", "method": "transfer", "params": [...]}'
```

---

## Atomic Swaps

**Supported Chains**: Bitcoin, Litecoin, Dogecoin, Cosmos Hub (11+ total)

**HTLC (Hash Time-Locked Contract)**:
1. Initiator creates HTLC with secret hash
2. Recipient creates HTLC on counterparty chain
3. Initiator reveals secret to claim funds
4. Recipient uses secret to claim on other chain

**Refund Protection**: Time-locked refunds after 24 hours

See `docs/advanced/atomic-swaps.md` for detailed guide.

---

## AI Governance

**Features**:
- Proposal submission and voting
- Quadratic voting (vote cost = votes²)
- Vote locking for time-weighted voting
- AI-assisted decision making

**Governance Process**:
1. Proposal created (requires minimum stake)
2. Voting period opens (configurable duration)
3. Votes tallied (quadratic or linear)
4. Proposal executes if quorum met
5. Parameters updated on-chain

---

## Security

### Validation Pipeline

**Transaction Validation**:
1. Signature verification (ECDSA)
2. Nonce check (replay protection)
3. Balance/UTXO verification
4. Fee calculation
5. Size limits

**Block Validation**:
1. Proof-of-work verification
2. Merkle root validation
3. Transaction validity
4. Timestamp checks
5. Difficulty verification

### Security Features

- **Nonce Tracking**: Prevents replay attacks
- **Rate Limiting**: API request throttling
- **Input Validation**: Schema-based validation
- **CORS Policies**: Configurable cross-origin rules
- **JWT Authentication**: Secure API access

---

## Performance

### Optimization Strategies

**Caching**:
- LRU cache for config files
- Response caching for block explorer
- Connection pooling for HTTP requests

**Indexing**:
- Address index for fast balance lookups
- Block index for efficient retrieval
- UTXO set for transaction validation

**Async Operations**:
- Asynchronous blockchain operations
- WebSocket for real-time updates
- Background sync processes

### Performance Metrics

**Throughput**: ~50 transactions/block
**Block Time**: 2 minutes (target)
**Sync Speed**: ~1000 blocks/minute (checkpoint sync)
**API Latency**: <100ms (cached), <500ms (uncached)

---

## Configuration

### Environment Variables

```bash
XAI_NETWORK=testnet              # Network selection
XAI_PORT=18545                   # P2P port
XAI_RPC_PORT=18546               # RPC port
XAI_DATA_DIR=~/.xai              # Data directory
XAI_LOG_LEVEL=INFO               # Logging level
MINER_ADDRESS=XAI...             # Mining reward address
XAI_PARTIAL_SYNC_ENABLED=1       # Enable checkpoint sync
```

See `.env.example` for complete configuration options.

---

## Monitoring

**Prometheus Metrics**: Available at `:12001/metrics`
**Grafana Dashboards**: Pre-configured in `monitoring/`
**Structured Logging**: JSON logs for aggregation

---

## Additional Resources

- **Whitepaper**: `WHITEPAPER.md`
- **API Reference**: `docs/api/`
- **CLI Guide**: `docs/CLI_GUIDE.md`
- **Architecture Review**: `ARCHITECTURE_REVIEW.md`

---

*Last Updated: January 2025 | XAI Version: 0.2.0*
