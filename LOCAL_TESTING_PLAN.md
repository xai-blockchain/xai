# XAI Project - Local Testing Plan (v4 - Definitive Edition)

This document is the definitive and most exhaustive local testing plan for the XAI project. It includes standard, advanced, and esoteric test cases to ensure maximum stability, security, and robustness. **This is the final version.**

## Phase 1: Primitives & Static Analysis

*   **[x] 1.1: Linter and Static Analysis:** `flake8 src/ tests/` ✅ COMPLETED - Fixed all 77 critical errors (2025-12-13)
*   **[x] 1.2: Unit Tests:** `pytest -m unit` - ✅ COMPLETED (266/266 passing - 100%) (2025-12-13)
    - test_blockchain.py: 61/61 passing ✅
    - test_config.py: 31/31 passing ✅
    - test_transaction_validator.py: 12/12 passing ✅
    - test_token_burning.py: 14/14 passing ✅
    - test_supply_cap.py: 17/17 passing ✅
    - test_xai_token.py: 12/12 passing ✅
    - test_chain_validator.py: 13/13 passing ✅
    - test_config_manager.py: 18/18 passing ✅
    - test_account_abstraction.py: 21/21 passing ✅
    - test_mempool_security.py: 21/21 passing ✅
    - test_peer_security.py: 19/19 passing ✅
    - test_ai_bridge.py: 1/1 passing ✅
    - test_reorg_simulator.py: 2/2 passing ✅
    - test_wallet.py: 24/24 passing ✅
    - **All fixes committed**: config ALLOW_CHAIN_RESET, transaction coinbase addresses, validator signature checking, exception handling, test fixtures, governance vote fee exemption, nonce test scenario, account_abstraction address validation, mempool utxo_stub parameter, wallet logger extra parameter
*   **[x] 1.3: Integration Tests:** `pytest -m integration` - ✅ COMPLETED (1/1 passing - 100%) (2025-12-13)
    - test_security_webhook_forwarder.py: 1/1 passing ✅
    - Installed missing dependency: flask-cors
*   **[x] 1.4: API Endpoint Tests:** `pytest tests/api/` - ✅ COMPLETED (1 test skipped - requires running node) (2025-12-13)
    - test_openapi_contract.py: Skipped (requires API_BASE_URL environment variable pointing to running node)
    - Note: This test will be run in Phase 2 after node initialization
*   **[x] 1.5: Verify Crypto Primitives:** ✅ COMPLETED (19/19 tests passing - 100%) (2025-12-13)
    - test_crypto_primitives.py: 19 tests covering SHA-256, ECDSA signatures, public key derivation, address generation, edge cases
    - Verified NIST test vectors for SHA-256
    - Tested signature generation, verification, and tampering detection
    - Cross-validated with wallet functionality
*   **[x] 1.6: Verify Encoding Primitives:** ✅ COMPLETED (20/20 tests passing - 100%) (2025-12-13)
    - test_encoding_primitives.py: 20 tests covering canonical JSON, transaction/block serialization, UTXO encoding, network messages
    - Verified canonical JSON determinism and key ordering for consensus
    - Tested transaction and block serialization roundtrips
    - Validated edge cases (zero amounts, large metadata, Unicode)

## Phase 2: Single-Node Lifecycle & Configuration

*   **[ ] 2.1: Genesis & Initialization:** Verify the node's initialization process and genesis block creation.
*   **[ ] 2.2: Exhaustive Configuration Testing:**
    *   **Description:** Script the modification of every parameter in the node's configuration file(s) to verify its behavior changes as expected or fails gracefully.
    *   **Action:** Focus on PoW parameters (e.g., block reward, difficulty), P2P settings, and mempool configuration.
*   **[ ] 2.3: CLI Command Verification:**
    *   **Description:** Test every single CLI command and subcommand provided by the `xaid` client.
    *   **Action:** Script the execution of all commands with valid and invalid parameters.

## Phase 3: Multi-Node Network & Consensus (PoW)

*   **[ ] 3.1: Multi-Node Network Baseline:** `docker-compose -f docker-compose.testnet.yml up -d`
*   **[ ] 3.2: Automated Testnet Suite:** `pytest tests/testnet/`
*   **[ ] 3.3: Orphan Block Handling:** Manually feed a node a block before its parent to ensure it's not discarded.
*   **[ ] 3.4: Network Latency & Jitter:** Use `tc` to simulate poor network conditions, observing its effect on natural fork rates and block propagation.
*   **[ ] 3.5: Difficulty Adjustment Algorithm:** Test that the PoW difficulty adjusts correctly in response to both increases and decreases in network hashrate.

## Phase 4: Comprehensive Security & Attack Simulation

*   **[ ] 4.1: Automated Security Suites:** `pytest -m security`, `pytest tests/fuzzing/`, `pytest tests/chaos/`
*   **[ ] 4.2: 51% Attack (Deep Re-org):** Isolate a minority of nodes, have them mine a longer private chain, and test the mainnet's ability to re-org correctly upon reconnection.
*   **[ ] 4.3: Selfish Mining Simulation:** Use a custom client to simulate a selfish mining attack and analyze its profitability on the testnet.
*   **[ ] 4.4: Transaction Malleability & Double-Spend:** Attempt to create two transactions with different txids from the same UTXO and ensure only one is ever confirmed.
*   **[ ] 4.5: Timestamp Manipulation (Time-Drift Attack):** Attempt to mine blocks with invalid timestamps (too far in the past or future) and verify they are rejected.
*   **[ ] 4.6: AI Governance & Smart Contract Exploits:** Run dedicated exploit scenarios against the AI Governance and Smart Contract engines. `pytest tests/xai_tests/`
*   **[ ] 4.7: RPC Endpoint Hardening:** Fuzz test all public-facing RPC endpoints with malformed requests.

## Phase 5: Advanced State, Economics & Upgrades

*   **[ ] 5.1: State Snapshot & Restore (UTXO):** Test a new node's ability to bootstrap from a UTXO snapshot.
*   **[ ] 5.2: State Pruning (Block Data):** Verify that pruning old block data (while retaining the UTXO set) works and reduces disk usage.
*   **[ ] 5.3: Fee Market & Miner Prioritization:** Test that miners correctly prioritize transactions based on fees.
*   **[ ] 5.4: Hard Fork (Software Upgrade):** Test a planned hard fork by having all nodes stop, upgrade their binary, and restart, ensuring the new consensus rules are followed.

## Phase 6: Cross-Chain Interoperability

*   **[ ] 6.1: Atomic Swaps (XAI <-> BTC, ETH):** Test HTLC-based atomic swaps with local `bitcoind` (regtest) and Ethereum (Anvil) nodes, covering both success and refund paths.

## Phase 7: Destructive & Long-Running Tests

*   **[ ] 7.1: Database Corruption Test:** Intentionally corrupt a node's database files (`utxo_set.db`, `blocks/`) while stopped and verify it fails with a clear error on restart.
*   **[ ] 7.2: Resource Constraint Test:** Run a node with restricted RAM and CPU to define minimum system requirements.
*   **[ ] 7.3: Long-Running Stability (Soak Test):** Run the testnet under a continuous, mixed load for 24-48 hours, monitoring for memory leaks or performance degradation.
*   **[ ] 7.4: E2E and Performance Suites:** Run the final, slowest test suites. `pytest tests/e2e/`, `pytest -m performance --runslow`

This v4 plan represents the full scope of local testing that can be performed.