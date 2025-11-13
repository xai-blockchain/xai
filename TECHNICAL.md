# XAI Blockchain: Technical Specifications

**Version 0.2.0**
**Last Updated**: January 2025

## 1. Network Parameters

### 1.1 Mainnet Configuration

```
Network ID:           0x5841
Genesis File:         genesis_new.json
Genesis Timestamp:    1704067200 (Unix timestamp)
Default Port:         8545
RPC Port:             8546
Address Prefix:       AIXN
```

### 1.2 Testnet Configuration

```
Network ID:           0xABCD
Genesis File:         genesis_testnet.json
Genesis Timestamp:    1704067200 (Unix timestamp)
Default Port:         18545
RPC Port:             18546
Address Prefix:       TXAI
Faucet:               Enabled (100 test XAI)
```

## 2. Consensus Specifications

### 2.1 Proof-of-Work Parameters

```
Algorithm:              SHA-256
Initial Difficulty:     4 (mainnet), 2 (testnet)
Target Block Time:      120 seconds (2 minutes)
Difficulty Adjustment:  Dynamic based on recent block times
Minimum Difficulty:     1
```

### 2.2 Block Structure

```json
{
  "index": "integer (block height)",
  "timestamp": "float (Unix timestamp)",
  "transactions": "array of transaction objects",
  "proof": "integer (nonce)",
  "previous_hash": "string (SHA-256 hex)",
  "merkle_root": "string (SHA-256 hex of transaction tree)",
  "miner": "string (miner address)",
  "difficulty": "integer (current difficulty)",
  "version": "integer (block version number)"
}
```

### 2.3 Block Validation Rules

1. `hash(block) < difficulty_target`
2. `previous_hash` matches hash of block at `index - 1`
3. `merkle_root` matches computed root of transactions
4. `timestamp` within acceptable range (not too far in future)
5. All transactions are valid
6. Coinbase transaction reward = block_reward + total_fees
7. Block size within limits

### 2.4 Difficulty Adjustment Algorithm

```python
def adjust_difficulty(blockchain):
    """
    Adjusts difficulty every N blocks based on actual vs target time
    """
    ADJUSTMENT_WINDOW = 100  # blocks
    TARGET_TIME = 120  # seconds per block

    if len(blockchain) % ADJUSTMENT_WINDOW != 0:
        return current_difficulty

    recent_blocks = blockchain[-ADJUSTMENT_WINDOW:]
    actual_time = recent_blocks[-1].timestamp - recent_blocks[0].timestamp
    expected_time = ADJUSTMENT_WINDOW * TARGET_TIME

    adjustment_factor = expected_time / actual_time
    new_difficulty = current_difficulty * adjustment_factor

    # Limit adjustment per window
    new_difficulty = max(new_difficulty, current_difficulty * 0.25)
    new_difficulty = min(new_difficulty, current_difficulty * 4.0)

    return max(1, int(new_difficulty))
```

## 3. Economic Specifications

### 3.1 Supply Parameters

```
Maximum Supply:         121,000,000 XAI
Initial Block Reward:   12 XAI
Halving Interval:       262,800 blocks
Minimum Block Reward:   0.00000001 XAI (when halvings complete)
```

### 3.2 Reward Schedule

```
Block Range              Reward      Annual Issuance*
0 - 262,799              12 XAI      3,153,600 XAI
262,800 - 525,599        6 XAI       1,576,800 XAI
525,600 - 788,399        3 XAI       788,400 XAI
788,400 - 1,051,199      1.5 XAI     394,200 XAI
1,051,200 - 1,313,999    0.75 XAI    197,100 XAI
...continues until negligible

* Assuming 2-minute block time (262,800 blocks/year)
```

### 3.3 Fee Structure

```
Minimum Transaction Fee:    0.0001 XAI
Fee Calculation:            Dynamic based on transaction size and priority
Trade Fee (Wallet Trades):  0.001 (mainnet), 0.002 (testnet)
Trade Fee Recipient:        AIXNTRADEFEE (mainnet), TXAITRADEFEE (testnet)
```

### 3.4 Genesis Distribution

The genesis block contains a premine allocation. The SHA-256 hash of the genesis file is:

```
Testnet: 59b30b2d8525512cbd5715b24546d73b540ddb575d3778fdbdff02ba245a9141
Mainnet: (to be determined at mainnet launch)
```

All nodes verify the genesis file hash on startup. Mismatched hashes cause the node to refuse to start.

## 4. Transaction Specifications

### 4.1 Transaction Structure

```json
{
  "sender": "string (address)",
  "recipient": "string (address)",
  "amount": "float (XAI amount)",
  "fee": "float (transaction fee)",
  "timestamp": "float (Unix timestamp)",
  "signature": "string (ECDSA signature)",
  "tx_type": "string (transaction type)",
  "tx_hash": "string (SHA-256 of transaction data)",
  "nonce": "integer (sender transaction counter)",
  "data": "object (type-specific data)"
}
```

### 4.2 Transaction Types

```
STANDARD:       Basic value transfer
MULTISIG:       Multi-signature transaction
TIME_CAPSULE:   Time-locked transaction
CONTRACT:       Smart contract interaction
ATOMIC_SWAP:    Cross-chain exchange
GOVERNANCE:     Governance proposal or vote
BURN:           Token burning (supply reduction)
```

### 4.3 Transaction Validation

Required checks:
1. Valid signature from sender
2. Sender has sufficient balance (amount + fee)
3. No double-spend (UTXOs not already spent)
4. Nonce is correct (sequential)
5. Timestamp within acceptable range
6. Transaction size within limits
7. Fee meets minimum threshold
8. Type-specific validation passes

### 4.4 UTXO Model

```json
{
  "tx_hash": "string (source transaction)",
  "output_index": "integer (position in transaction outputs)",
  "address": "string (owner address)",
  "amount": "float (XAI amount)",
  "script": "string (locking script)",
  "is_spent": "boolean",
  "spent_in_tx": "string (spending transaction hash, if spent)"
}
```

## 5. Cryptographic Specifications

### 5.1 Hash Functions

```
Block Hashing:          SHA-256
Transaction Hashing:    SHA-256
Merkle Tree:            SHA-256
Address Generation:     SHA-256 + RIPEMD-160
```

### 5.2 Signature Algorithm

```
Algorithm:              ECDSA (Elliptic Curve Digital Signature Algorithm)
Curve:                  secp256k1
Key Length:             256 bits
Signature Format:       DER encoding
```

### 5.3 Address Format

```
Public Key → SHA-256 → RIPEMD-160 → Base58Check → Address

Mainnet Address: AIXN + base58(version + pubkey_hash + checksum)
Testnet Address: TXAI + base58(version + pubkey_hash + checksum)

Address Length: Variable (typically 34-35 characters)
Example Mainnet: AIXNa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5
Example Testnet: TXAIa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5
```

### 5.4 HD Wallet Derivation

```
Standard:               BIP32, BIP44
Derivation Path:        m/44'/0'/0'/0/0 (default, configurable)
Mnemonic:               BIP39 (12-24 word phrases)
Key Stretching:         PBKDF2-HMAC-SHA512
```

## 6. Smart Contract Specifications

### 6.1 Contract Deployment

```json
{
  "type": "contract_deploy",
  "bytecode": "hex string",
  "constructor_args": "array",
  "gas_limit": "integer",
  "value": "float (initial funding)"
}
```

### 6.2 Gas Model

```
Operation               Gas Cost
ADD/SUB/MUL/DIV        3
COMPARISON             3
HASH                   30
STORAGE_READ           200
STORAGE_WRITE          5,000
CONTRACT_CALL          700
CONTRACT_CREATE        32,000
```

### 6.3 Contract Execution

```
Stack Size:             1024 items
Max Call Depth:         256
Max Contract Size:      24,576 bytes
Execution Timeout:      5 seconds
State Trie:             Merkle Patricia Tree
```

## 7. Atomic Swap Specifications

### 7.1 HTLC Structure

```json
{
  "type": "atomic_swap",
  "initiator": "string (XAI address)",
  "participant": "string (XAI address)",
  "amount": "float (XAI)",
  "hash_lock": "string (SHA-256 hash)",
  "time_lock": "integer (Unix timestamp)",
  "counterparty_chain": "string (BTC, ETH, etc.)",
  "counterparty_address": "string",
  "counterparty_amount": "float",
  "state": "string (PENDING, COMPLETED, REFUNDED)"
}
```

### 7.2 Swap Protocol Timing

```
Phase 1: Initialization (Initiator creates HTLC on XAI)
    Time: T0
    Timeout: T0 + 48 hours

Phase 2: Participation (Participant creates HTLC on counterparty chain)
    Time: T0 + 1 hour (typical)
    Timeout: T0 + 24 hours (must be before Phase 1 timeout)

Phase 3: Redemption (Initiator reveals preimage)
    Time: Within Phase 2 timeout

Phase 4: Completion (Participant claims XAI)
    Time: After preimage reveal, before timeouts
```

### 7.3 Supported Chains

```
Bitcoin (BTC)           Native HTLC support
Ethereum (ETH)          Smart contract HTLC
Litecoin (LTC)          Native HTLC support
Bitcoin Cash (BCH)      Native HTLC support
Dogecoin (DOGE)         Native HTLC support
Monero (XMR)            Hash lock protocol
Zcash (ZEC)             Native HTLC support
Dash (DASH)             Native HTLC support
Stellar (XLM)           Smart contract HTLC
Ripple (XRP)            Escrow-based HTLC
Cardano (ADA)           Smart contract HTLC
```

## 8. AI Governance Specifications

### 8.1 Proposal Structure

```json
{
  "proposal_id": "string (unique identifier)",
  "title": "string",
  "description": "string (markdown)",
  "proposer": "string (address)",
  "created_at": "integer (Unix timestamp)",
  "voting_start": "integer (Unix timestamp)",
  "voting_end": "integer (Unix timestamp)",
  "proposal_type": "string (PARAMETER_CHANGE, FEATURE, EMERGENCY)",
  "status": "string (PENDING, ACTIVE, PASSED, REJECTED, EXECUTED)"
}
```

### 8.2 AI Analysis Output

```json
{
  "proposal_id": "string",
  "analysis_timestamp": "integer",
  "technical_feasibility": {
    "score": "float (0-10)",
    "assessment": "string",
    "concerns": "array of strings"
  },
  "security_impact": {
    "risk_level": "string (LOW, MEDIUM, HIGH, CRITICAL)",
    "vulnerabilities": "array of strings",
    "mitigations": "array of strings"
  },
  "economic_impact": {
    "supply_effect": "string",
    "fee_impact": "string",
    "market_considerations": "string"
  },
  "implementation_estimate": {
    "complexity": "string (LOW, MEDIUM, HIGH)",
    "estimated_blocks": "integer",
    "dependencies": "array of strings"
  },
  "recommendation": "string (APPROVE, REJECT, NEEDS_REVISION)",
  "confidence": "float (0-1)"
}
```

### 8.3 Voting Parameters

```
Minimum Participation:      10% of circulating supply
Approval Threshold:         66% of votes cast
Voting Period:              100,800 blocks (~14 days)
Vote Weight:                1 XAI = 1 vote
Vote Types:                 FOR, AGAINST, ABSTAIN
```

### 8.4 Execution

```
Execution Delay:            7,200 blocks (~10 days after approval)
Emergency Fast-Track:       Requires 80% approval, 24-hour delay
Cancellation:               Proposer can cancel before voting ends
Override:                   Manual intervention by core developers (documented)
```

## 9. Time Capsule Specifications

### 9.1 Time Capsule Structure

```json
{
  "type": "time_capsule",
  "capsule_id": "string (unique identifier)",
  "creator": "string (address)",
  "recipient": "string (address)",
  "amount": "float (locked XAI)",
  "created_at": "integer (Unix timestamp)",
  "unlock_time": "integer (Unix timestamp)",
  "message": "string (optional encrypted message)",
  "is_unlocked": "boolean",
  "claimed_at": "integer (Unix timestamp when claimed)"
}
```

### 9.2 Locking Rules

```
Minimum Lock Time:          1 hour (3,600 seconds)
Maximum Lock Time:          100 years (Unix timestamp < 4102444800)
Minimum Amount:             0.01 XAI
Early Unlock:               Not permitted
Transfer:                   Cannot change recipient after creation
```

### 9.3 Unlock Process

```
1. Check current_timestamp >= unlock_time
2. Verify recipient signature
3. Create transaction from capsule address to recipient
4. Mark capsule as unlocked
5. Add to blockchain
```

## 10. Multi-Signature Specifications

### 10.1 Multi-Sig Wallet Structure

```json
{
  "wallet_id": "string (address)",
  "required_signatures": "integer (m)",
  "total_signers": "integer (n)",
  "signers": [
    {
      "address": "string",
      "public_key": "string",
      "name": "string (optional)"
    }
  ],
  "created_at": "integer",
  "balance": "float"
}
```

### 10.2 Transaction Signing

```
Common Configurations:
- 2-of-3: Personal wallet with backup
- 3-of-5: Corporate treasury
- 5-of-7: DAO governance
- Custom: Any m-of-n where m ≤ n

Maximum Signers:            15
Signature Timeout:          7 days (after which unsigned tx can be cancelled)
Partial Signatures:         Stored off-chain until threshold met
```

### 10.3 Signing Process

```
1. Initiator creates transaction
2. Collects signatures from m signers
3. Combines signatures into single transaction
4. Broadcasts to network
5. Validators verify m-of-n signatures valid
6. Transaction included in block
```

## 11. Network Protocol Specifications

### 11.1 Peer-to-Peer Protocol

```
Protocol Version:           1
Maximum Peers:              125 (50 inbound, 75 outbound)
Peer Discovery:             DNS seeds, peer exchange
Connection Timeout:         30 seconds
Ping Interval:              120 seconds
Max Message Size:           32 MB
```

### 11.2 Message Types

```
TYPE                SIZE        DESCRIPTION
version             100 bytes   Protocol handshake
verack              24 bytes    Version acknowledgment
ping                32 bytes    Keepalive request
pong                32 bytes    Keepalive response
getaddr             24 bytes    Request peer addresses
addr                Variable    Peer address list
inv                 Variable    Inventory announcement
getdata             Variable    Request data
block               Variable    Block data
tx                  Variable    Transaction data
getblocks           Variable    Request block headers
getheaders          Variable    Request headers only
headers             Variable    Block headers
mempool             24 bytes    Request mempool contents
```

### 11.3 Synchronization Protocol

```
Initial Block Download:
1. Connect to peers
2. Send getblocks with known block hashes
3. Receive inv messages with available blocks
4. Send getdata for missing blocks
5. Validate and store blocks
6. Request next batch
7. Repeat until synchronized

Header-First Sync:
1. Download all headers
2. Verify header chain (PoW, timestamps)
3. Download full blocks
4. Validate transactions
5. Build UTXO set
```

## 12. Storage Specifications

### 12.1 Directory Structure

```
data/
├── blocks/                 # Block storage
│   ├── 00000/             # Directory per 1000 blocks
│   │   ├── block_00000.json
│   │   ├── block_00001.json
│   │   └── ...
│   └── 00001/
├── index/                  # Indices
│   ├── height_index.json  # Block height → file mapping
│   ├── tx_index.json      # Transaction → block mapping
│   └── address_index.json # Address → transactions
├── chainstate/            # UTXO set
│   └── utxo_set.db        # Current unspent outputs
├── wallets/               # Wallet files
└── logs/                  # Node logs
```

### 12.2 File Formats

```
Block Files:            JSON (line-delimited for large files)
Index Files:            JSON with compression
UTXO Database:          LevelDB or similar key-value store
Wallet Files:           Encrypted JSON
```

### 12.3 Pruning

```
Pruning Mode:           Optional
Retain Blocks:          Last 288 blocks (~24 hours minimum)
Pruned Node:            Can validate new blocks, cannot serve old blocks
Full Archive Node:      Stores entire blockchain history
```

## 13. API Specifications

### 13.1 REST API Endpoints

```
Node Information:
GET  /info                  # Node status, chain height, version
GET  /peers                 # Connected peer list

Blockchain:
GET  /chain                 # Full blockchain (use with caution)
GET  /chain/height          # Current block height
GET  /block/<height>        # Block by height
GET  /block/hash/<hash>     # Block by hash
GET  /blocks/range          # Block range (query params: start, end)

Transactions:
GET  /transaction/<hash>    # Transaction by hash
POST /transaction           # Broadcast transaction
GET  /mempool               # Pending transactions

Wallet:
POST /wallet/create         # Create new wallet
GET  /wallet/balance/<addr> # Address balance
POST /wallet/send           # Send transaction
GET  /wallet/history/<addr> # Transaction history

Mining:
POST /mining/start          # Start mining
POST /mining/stop           # Stop mining
GET  /mining/status         # Mining status

Governance:
GET  /governance/proposals  # List proposals
POST /governance/propose    # Submit proposal
POST /governance/vote       # Cast vote

Time Capsules:
POST /timecapsule/create    # Create time capsule
GET  /timecapsule/<id>      # Get capsule info
POST /timecapsule/claim     # Claim unlocked capsule

Atomic Swaps:
POST /swap/initiate         # Initiate atomic swap
POST /swap/participate      # Participate in swap
POST /swap/redeem           # Redeem swap
POST /swap/refund           # Refund after timeout

Compliance:
GET  /regulator/flagged     # Flagged transactions
GET  /history/<addr>        # Address history with metadata
```

### 13.2 Rate Limiting

```
Default Rate Limit:         120 requests per 60 seconds
Burst Allowance:           10 requests
Rate Limit Headers:         X-RateLimit-Limit, X-RateLimit-Remaining
Exceeded Response:          429 Too Many Requests
```

### 13.3 Authentication

```
API Key (Optional):         X-API-Key header
JWT Token (Optional):       Authorization: Bearer <token>
Public Endpoints:           No auth required
Protected Endpoints:        Wallet operations, admin functions
```

## 14. Security Specifications

### 14.1 Validation Thresholds

```
Block Confirmations:        6 (for high-value transactions)
Transaction Confirmation:   1 (for low-value, 6+ for high-value)
Reorganization Limit:       100 blocks maximum reorg depth
Timestamp Tolerance:        2 hours into future
```

### 14.2 DOS Protection

```
Connection Limits:          50 connections per IP (inbound)
Request Rate Limits:        120 req/min per IP
Max Block Size:             2 MB
Max Transaction Size:       100 KB
Mempool Size Limit:         300 MB
Mempool Expiry:             72 hours
```

### 14.3 Attack Mitigation

```
Double-Spend:               UTXO validation, confirmation requirements
51% Attack:                 PoW difficulty makes attack expensive
Sybil Attack:               PoW provides sybil resistance
Eclipse Attack:             Diverse peer connections (8+ outbound)
Spam Attack:                Fee requirements, rate limits
Time-Warp Attack:           Timestamp validation
Selfish Mining:             Block propagation optimizations
```

## 15. Performance Benchmarks

### 15.1 Throughput

```
Block Time:                 120 seconds (target)
Block Size:                 2 MB maximum
Transactions per Block:     ~2,000 (depending on tx size)
Throughput:                 ~16 tx/second average
Peak Throughput:            ~33 tx/second (with optimization)
```

### 15.2 Validation Performance

```
Block Validation:           <1 second (typical)
Transaction Validation:     <10 ms (typical)
Signature Verification:     ~0.5 ms per signature
UTXO Lookup:                <1 ms (indexed)
```

### 15.3 Storage Requirements

```
Block Size Average:         500 KB (typical)
Annual Growth:              ~13 GB per year (at full capacity)
UTXO Set:                   ~500 MB (estimate after 1 year)
Full Node Storage:          20 GB recommended minimum
Pruned Node Storage:        2 GB minimum
```

### 15.4 Network Bandwidth

```
Inbound:                    ~1 Mbps average
Outbound:                   ~2 Mbps average (serving blocks)
Peak:                       ~10 Mbps during sync
Monthly Data:               ~30 GB for full node
```

## 16. Compatibility

### 16.1 Client Software

```
Reference Implementation:   Python 3.9+
Alternative Clients:        Open for development
Electron Desktop:           Windows, macOS, Linux
Browser Extension:          Chrome, Firefox, Edge (roadmap)
```

### 16.2 Wallet Compatibility

```
Standard Wallets:           BIP32/BIP39/BIP44 compliant
Hardware Wallets:           Ledger support (roadmap)
Paper Wallets:              Supported
Brain Wallets:              Not recommended
```

### 16.3 Exchange Integration

```
Deposit/Withdrawal API:     Standard JSON-RPC
Address Generation:         BIP44 derivation
Confirmation Requirement:   6 blocks recommended
Webhook Support:            Transaction notifications
```

## 17. Testing

### 17.1 Test Coverage

```
Unit Tests:                 Core functionality
Integration Tests:          Component interactions
End-to-End Tests:           Full node operation
Security Tests:             Attack vectors
Performance Tests:          Benchmark validation
```

### 17.2 Test Network

```
Testnet Purpose:            Development and testing
Reset Capability:           Can reset for testing
Free Coins:                 Faucet provides test XAI
Reduced Security:           Lower difficulty, faster blocks
Isolation:                  Separate from mainnet
```

## 18. Version History

### Version 0.2.0 (January 2025)
- Directory-based blockchain storage
- Electron desktop wallet
- Enhanced security features
- Improved documentation

### Version 0.1.0 (2024)
- Initial blockchain implementation
- Core consensus mechanism
- Wallet functionality
- Mining capabilities
- AI governance framework
- Atomic swap support

## 19. Future Specifications

### Planned Features
- Light client protocol (SPV)
- Mobile wallet bridge
- Hardware wallet integration
- Embedded wallet system
- Fiat on-ramp integration
- Enhanced smart contract VM
- Layer 2 scaling solutions
- Cross-chain bridges
- Privacy enhancements

### Research Areas
- Zero-knowledge proofs
- Post-quantum cryptography
- Sharding
- Alternative consensus mechanisms
- Governance improvements

---

**Document Version**: 0.2.0
**Last Updated**: January 2025
**Specification Status**: Living document (subject to updates)
**Repository**: https://github.com/decristofaroj/xai
