# XAI Blockchain - Technical Overview

## Architecture

XAI is a proof-of-work blockchain with integrated AI systems for governance and user assistance.

### Core Components

**Blockchain Layer**
- Block time: 2 minutes
- Mining algorithm: SHA-256 based proof-of-work
- Block reward: 60 XAI (with halving every 9 months)
- Total supply: 120,000,000 XAI
- Transaction model: UTXO-based

**Consensus**
- Proof-of-work for block validation
- Longest chain rule
- Difficulty adjustment every 2016 blocks

### AI Systems

**Governance AI**
- Community proposes blockchain improvements
- Voting weighted by coin holdings (70%) and AI donations (30%)
- Multi-AI collaboration (2-3 AIs work together)
- Node operator consensus (25+ operators required)
- AI implements approved changes after testnet validation

**Personal AI**
- Individual users bring their own AI API key
- Assists with atomic swaps, smart contracts, transactions
- Cannot modify blockchain consensus
- User pays own AI costs
- Rate limited to 100 requests/hour per user

### Key Features

**Atomic Swaps**
- Cross-chain swaps with 11 cryptocurrencies
- Hash Time-Locked Contracts (HTLC)
- No external APIs (on-chain price discovery)
- Supported: BTC, ETH, LTC, DOGE, XMR, BCH, USDT, ZEC, DASH, USDC, DAI

**Smart Contracts**
- Python-based execution environment
- Turing-complete
- Gas-based fee model
- Deployed via transactions

**Enhanced Voting**
- Continuous coin-holding verification
- Vote invalidated if coins sold during voting period
- Mandatory 1-week minimum voting timeline
- Multi-signature governance execution

**Time Capsules**
- Lock XAI or other cryptocurrencies until future date
- Cross-chain time-locks via HTLC
- Optional messages and beneficiaries
- Use cases: savings, gifts, inheritance

### Distribution

**Genesis Allocation (17%)**
- 11 mystery wallets: 1,004,500 XAI (immediate)
- Founders vesting: 3,000,000 XAI (12-year vesting)
- Development fund: 10,000,000 XAI (10-year vesting)
- Marketing fund: 6,000,000 XAI (6-year vesting)
- Operations fund: 400,000 XAI (node bonuses)

**Early Adopter Program (4.86%)**
- 40,069 wallets reserved for early participants
- Multiple tiers with varying allocations
- Wallet assignment system for node operators

**Ongoing Mining (77.76%)**
- 93,310,500 XAI available through mining
- Block reward halving every 9 months
- Lucky blocks (~1%) award 2x reward randomly

**Easter Eggs (0.375%)**
- 100 hidden treasure wallets (1,000 XAI each)
- Mystery airdrops at 3, 6, and 12 months
- Cryptic clues hidden in block metadata

### Network

**Node Communication**
- JSON-RPC API over HTTP
- WebSocket support for real-time updates
- Peer-to-peer gossip protocol
- Default port: 8545 (configurable)

**API Endpoints**
- `/chain` - Blockchain data
- `/transactions` - Transaction submission
- `/mining/*` - Mining control
- `/governance/*` - Voting and proposals
- `/personal-ai/*` - Personal AI assistance
- `/ai/*` - AI safety controls
- `/time-capsule/*` - Time capsule operations
- `/ws` - WebSocket connection

### Security

**Wallet Assignment**
- Sybil resistance mechanisms
- One wallet per node instance
- Various qualification criteria

**Timelock Mechanisms**
- Genesis allocations locked until vesting dates
- Smart contract time-based execution
- HTLC timeout enforcement

**AI Safety Controls**
- Instant Personal AI request cancellation (user-level)
- Trading bot emergency stop
- Governance AI task pause/abort (community vote)
- Global AI kill switch (security emergencies)
- Users have instant control over AI affecting their assets

**AI Safety Boundaries**
- Personal AI cannot modify consensus rules
- All AI actions require user signature
- Rate limiting prevents abuse
- Governance AI changes require community approval

### Technical Specifications

**Block Structure**
```
{
  "index": integer,
  "timestamp": unix_timestamp,
  "transactions": array,
  "previous_hash": string,
  "nonce": integer,
  "hash": string,
  "difficulty": integer
}
```

**Transaction Structure**
```
{
  "txid": string,
  "sender": address,
  "recipient": address,
  "amount": float,
  "fee": float,
  "timestamp": unix_timestamp,
  "signature": string,
  "public_key": string
}
```

**Difficulty Adjustment**
- Target: 2-minute block time
- Adjustment: Every 2016 blocks
- Algorithm: Bitcoin-style difficulty retargeting

### Development

**Dependencies**
- Python 3.8+
- Flask (API server)
- ecdsa (cryptography)
- hashlib (hashing)
- requests (networking)

**File Structure**
```
core/
  blockchain.py        - Core blockchain logic
  node.py             - Node and networking
  wallet.py           - Wallet operations
  ai_governance.py    - Governance AI system
  personal_ai_assistant.py - Personal AI system
  atomic_swaps.py     - Cross-chain swaps
  smart_contracts.py  - Contract execution
```

### Running a Node

**Basic Node**
```bash
python core/node.py
```

**Mining Node**
```bash
python core/node.py --miner YOUR_ADDRESS
```

**Configuration**
```bash
export XAI_HOST="0.0.0.0"
export XAI_PORT="8545"
python core/node.py
```

**With Peers**
```bash
python core/node.py --peers http://peer1:8545 http://peer2:8545
```

### Pre-Mine

The blockchain includes 64,800 pre-mined blocks (~6 months at 2 min/block) distributed across early adopter wallets. Timestamps are randomized (±30 seconds) to simulate organic growth.

### License

MIT License - See LICENSE file
