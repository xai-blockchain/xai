# XAI Consensus & Networking Specification

This document is the implementation-tied specification for the XAI chain’s consensus and networking stack.  It is sourced directly from the production modules in `src/xai/core/blockchain.py`, `src/xai/core/node_consensus.py`, `src/xai/core/node_p2p.py`, `src/xai/core/node_api.py`, and `src/xai/core/peer_discovery.py`.  The goal is to give client implementers, infrastructure teams, and external auditors a single reference that explains how nodes maintain consensus, how they exchange data, and what invariants every peer must enforce.

## 1. Network & Node Roles

| Component | Description |
| --- | --- |
| Full node (`xai.core.node.BlockchainNode`) | Hosts the REST API, maintains local state on disk via `BlockchainStorage`, participates in mining, validation, and gossip. |
| Miner | A full node with mining enabled (`node_mining.py`).  Mining is optional but governed by the same consensus rules. |
| Bootstrap / discovery node | Any node configured in `peer_discovery.BootstrapNodes` (per-network seed lists).  They respond to `/peers/list` and `/peers/announce` to help new nodes join. |
| External clients | Wallets, dashboards, or monitoring agents that hit the HTTP API.  They authenticate using scoped API keys managed by `APIAuthManager`. |

Supported network profiles live in `src/xai/core/config.py`:

- **Mainnet** – default port `8545`, PoW difficulty `4`, faucet disabled.
- **Testnet** – default port `18545`, PoW difficulty `2`, faucet enabled, relaxed guards.
- **Devnet** – uses the local bootstrap list and developer settings.

All peers must pin the expected genesis hash via `Config.SAFE_GENESIS_HASHES` before taking part in consensus.

## 2. Data Structures

### 2.1 Transactions (`blockchain.Transaction`)

Fields: `txid`, `sender`, `recipient`, `amount`, `fee`, `timestamp`, `signature`, `public_key`, `tx_type`, `nonce`, `metadata`, `inputs`, `outputs`.

- UTXO based: `inputs`/`outputs` map to the `UTXOManager`.
- Coinbase/system actors (`COINBASE`, `SYSTEM`, `AIRDROP`) bypass signature enforcement.
- `txid` is `sha256` over deterministic JSON (`calculate_hash`).
- Signatures leverage `xai.core.crypto_utils` (backed by `cryptography`), and the sender address is derived from the public key hash, preventing rogue key substitution.

### 2.2 Blocks (`blockchain.Block`)

Fields: `index`, `timestamp`, `transactions`, `previous_hash`, `merkle_root`, `nonce`, `hash`, `difficulty`, `miner`.

- `merkle_root` is recalculated on load, deduplicating odd leaves.
- Proof-of-work target: prefix of `difficulty` zeroes (`"0" * difficulty`).
- `miner` is inferred from the first (coinbase) transaction to distribute rewards.

### 2.3 Chain State (`blockchain.Blockchain`)

Core parameters:

| Parameter | Value / Source |
| --- | --- |
| Initial reward | `12.0` XAI (`initial_block_reward`). |
| Halving interval | `262,800` blocks (≈1 year with `120s` block time). |
| Max supply | `121,000,000` XAI. |
| Difficulty | Mutable per network (`Blockchain.difficulty`), default `4`. |
| Storage | Append-only block files + UTXO snapshots managed by `BlockchainStorage`. |

Supporting modules: `TransactionValidator`, `UTXOManager`, `NonceTracker`, `WalletTradeManager`, and gamified reward helpers.

## 3. Consensus Algorithm

Consensus is Nakamoto-style proof-of-work augmented with deterministic validation:

1. **Transaction admission** (`Blockchain.add_transaction` + `TransactionValidator`):
   - Enforces signature validity, nonce monotonicity, UTXO coverage, ban-lists, and per-module guards (withdrawal limits, anti-whale, etc.).
2. **Mining** (`Block.mine_block`):
   - Miner builds a block with coinbase reward + pending transactions, recomputes `merkle_root`, increments `nonce` until `hash` meets the target.
3. **Block validation** (`ConsensusManager.validate_block`):
   - Hash correctness, PoW prefix, sequential `index`, `previous_hash`, monotonic timestamps.
4. **Transaction validation** (`validate_block_transactions`):
   - Re-verifies signatures, balance sufficiency (`Blockchain.get_balance`), and special transaction semantics.
5. **Fork choice** (`resolve_forks`, `should_replace_chain`):
   - Selects the longest valid chain; on equal length, compares cumulative work via `calculate_chain_work`.
   - `Blockchain.replace_chain` applies the new chain after reprocessing orphaned blocks.
6. **Integrity monitoring** (`check_chain_integrity`):
   - Detects index gaps, linkage failures, and double spends (`spent_outputs` map).

**Finality:** Probabilistic—operators should wait for ≥6 confirmations on mainnet-sized deployments.  The spec mandates identical validation logic across clients to keep fork choice deterministic.

## 4. Networking Layer

### 4.1 Transport Basics

- HTTP/HTTPS REST endpoints served by Flask (`node_api.py`).
- P2P clients use `xai.core.node_p2p.P2PNetworkManager`, which iterates over `self.peers` (a `Set[str]` of base URLs).
- All peer-to-peer requests include the `X-API-Key` header populated from `XAI_PEER_API_KEY` (see `Config.PEER_API_KEY`).  Requests without the shared peer key are rejected once `APIAuthManager` is enabled.
- Timeouts: `broadcast_transaction`/`broadcast_block` use `2s` POSTs, syncing uses `5–10s` GETs with pagination to avoid DoS.

### 4.2 Discovery Protocol (`peer_discovery.py`)

1. **Bootstrap** – Nodes seed their peer list from `BootstrapNodes.get_seeds(network_type)`.
2. **GetPeers** – `GET /peers/list` returns `{"peers": [...]}`, along with metadata (`PeerInfo.to_dict`) when served through `peer_discovery` utilities.
3. **Announce** – `POST /peers/announce` allows new peers to share their URL (handled in `peer_discovery.PeerDiscoveryProtocol.send_peers_announcement`).
4. **Quality scoring** – `PeerInfo` tracks success/failure counts, response latency, and removes dead peers after `timeout` seconds (default 3600s).
5. **Diversity controls** – The discovery loop prefers IP/geography diversity and periodic refreshes (every 5 minutes) to avoid clique formation.

### 4.3 Gossip Endpoints (subset)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/transaction/receive` | POST | Validated `PeerTransactionInput`; adds to mempool, returns `{ "txid": ... }`. |
| `/block/receive` | POST | Validated `PeerBlockInput`; deserializes via `Blockchain.deserialize_block`, runs consensus checks, returns new height. |
| `/blocks` | GET | Paginated JSON view used for P2P sync (`limit`, `offset`). |
| `/sync` | POST | Triggers `P2PNetworkManager.sync_with_network()`, returning whether the local chain was replaced. |
| `/peers` | GET | Enumerates the connected peer list. |
| `/peers/add` | POST | Adds a peer URL (validated by `PeerAddInput`). |
| `/peers/list` & `/peers/announce` | Discovery helpers under `peer_discovery` for exchanging peer tables. |

All payloads must conform to the Pydantic schemas in `src/xai/core/input_validation_schemas.py`, ensuring well-formed JSON before reaching business logic.

### 4.4 Message Schemas

```jsonc
// Transaction gossip payload
{
  "txid": "string sha256",
  "sender": "XAI...",
  "recipient": "XAI...",
  "amount": 12.5,
  "fee": 0.05,
  "timestamp": 1710000000,
  "signature": "hex",
  "public_key": "hex",
  "tx_type": "normal|treasure|...",
  "nonce": 5,
  "inputs": [{"txid": "...", "output_index": 0}],
  "outputs": [{"address": "XAI...", "amount": 12.45}],
  "metadata": {"memo": "..."}
}

// Block gossip payload
{
  "index": 12345,
  "timestamp": 1710000123,
  "transactions": [ /* array of Transaction payloads */ ],
  "previous_hash": "0000abc...",
  "merkle_root": "hash",
  "nonce": 82913,
  "hash": "0000ab42...",
  "difficulty": 4
}
```

### 4.5 Security Controls

- **API auth** – `APIAuthManager` enforces `X-API-Key` headers for both REST clients and peer traffic when `XAI_API_AUTH_REQUIRED=1`.
- **Scoped keys** – Keys are `user` (standard API) or `admin` (for `/admin/*`), tracked in `secure_keys/api_keys.json` plus append-only audit logs.
- **Rate limiting** – `RateLimiter` per IP or API key, configured via `XAI_API_RATE_LIMIT` and related env vars.
- **Security logging** – All peer events go through `log_security_event` which feeds Prometheus counters and webhook queues (`SecurityEventRouter`).
- **Peer quotas** – `P2PSecurityManager` (see earlier tasks) enforces inbound/outbound volume limits, reputation scoring, and DDoS protections.

## 5. Canonical Workflows

### 5.1 Transaction Propagation

1. Wallet submits to `/send` with a signed payload.
2. Node validates, records in mempool, then calls `Node.broadcast_transaction`.
3. Each peer receives `/transaction/receive`, re-runs signature and balance checks, and optionally re-broadcasts.

### 5.2 Block Propagation & Fork Choice

1. Miner mines block (`Block.mine_block`) and pushes it to peers via `/block/receive`.
2. Receiving node deserializes, validates, and adds the block.
3. Periodic `/sync` or startup sync fetches `/blocks` from peers, deserializes via `Blockchain.deserialize_chain`, and passes it to `ConsensusManager.should_replace_chain`.  Longest valid chain wins, with cumulative work as the tie breaker.

### 5.3 Peer Discovery Refresh

1. Node queries all known peers with `GET /peers/list`.
2. `PeerDiscoveryProtocol` scores responses, merges new addresses, and removes dead entries.
3. New addresses are added to `P2PNetworkManager.peers`, enabling subsequent block/transaction broadcasts.

## 6. Compliance Requirements for Alternative Clients

Any independent implementation must:

- Produce identical `Transaction`/`Block` JSON encodings.
- Enforce the validation sequence documented above (signature, nonce, UTXO, PoW, ordering).
- Respect the REST gossip endpoints and headers, including API key authentication.
- Implement longest-chain-plus-work fork choice and maintain orphan handling semantics (`Blockchain.orphan_blocks`).
- Emit `log_security_event` equivalents so that monitoring, alerting, and webhook retries stay in lockstep with the operational tooling introduced in `monitoring/`.

Following this specification guarantees compatibility with the reference client and keeps the network cohesive while we work toward the multi-client roadmap outlined in the governance tasks.
