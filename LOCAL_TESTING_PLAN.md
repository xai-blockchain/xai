# XAI Project - Local Testing Plan

This document outlines a comprehensive, ordered testing plan for the XAI blockchain project. It is designed to be executed by AI agents to ensure the stability, security, and functionality of the chain before cloud deployment. The plan is based on analysis of `pytest.ini` and the `tests/` directory structure.

## Phase 1: Local Sanity Checks & Unit Testing

This phase focuses on testing individual components in isolation. All commands should be run from the `xai` project root.

*   **[ ] 1.1: Run Linter and Static Analysis**
    *   **Description:** Check the Python codebase for style guide violations, programming errors, and suspicious constructs. (Assuming a linter like `flake8` or `pylint` is configured).
    *   **Command:**
        ```bash
        # Command depends on the specific linter used.
        flake8 src/
        # or
        pylint src/
        ```
    *   **Expected Outcome:** The command should pass with no errors.

*   **[ ] 1.2: Execute Unit Tests**
    *   **Description:** Run all fast-running unit tests across the project. This is the first line of defense against regressions.
    *   **Command:** `pytest -m unit`
    *   **Expected Outcome:** All unit tests should pass.

## Phase 2: Local Integration & Component Testing

This phase tests the interaction between different components on a single node.

*   **[ ] 2.1: Execute Integration Tests**
    *   **Description:** Run all integration tests that verify interactions between different modules of the blockchain node. These are typically slower than unit tests.
    *   **Command:** `pytest -m integration`
    *   **Expected Outcome:** All integration tests should pass.

*   **[ ] 2.2: Test API Endpoints**
    *   **Description:** Run tests specifically targeting the node's API/RPC endpoints.
    *   **Command:** `pytest tests/api/`
    *   **Expected Outcome:** All API tests should pass, confirming that endpoints are behaving as expected.

*   **[ ] 2.3: Genesis Block and Chain Initialization**
    *   **Description:** Test the creation of a valid genesis block and the initialization of a new chain from it. (Assuming a CLI tool `xaid`).
    *   **Command:**
        ```bash
        # This is an assumption based on common blockchain project structure.
        # The actual commands need to be found in the project's source/docs.
        rm -rf ~/.xai
        xaid init --chain-id="xai-test-1"
        # ... commands to add genesis accounts, etc.
        xaid start
        ```
    *   **Expected Outcome:** The node starts successfully without errors.

## Phase 3: Local Multi-Node Network Testing

This phase involves setting up a local, multi-node testnet to test network-level functionality. The `tests/testnet` directory suggests specific tests for this.

*   **[ ] 3.1: Multi-Node Network Setup**
    *   **Description:** Launch a 4-node local testnet. (Assuming a docker-compose setup exists).
    *   **Command:**
        ```bash
        # Assuming a docker-compose file for the testnet
        docker-compose -f docker-compose.testnet.yml up -d
        ```
    *   **Expected Outcome:** All 4 nodes should start, connect to each other, and start mining blocks (since it's PoW).

*   **[ ] 3.2: Run Testnet-Specific Tests**
    *   **Description:** Execute the suite of tests designed specifically for the multi-node environment.
    *   **Command:** `pytest tests/testnet/`
    *   **Expected Outcome:** All testnet tests should pass. This will likely cover P2P connectivity, transaction propagation, and basic consensus checks.

*   **[ ] 3.3: Basic Transaction Lifecycle (UTXO)**
    *   **Description:** Test the full lifecycle of a UTXO-based transaction: creation, signing, submission, propagation, and inclusion in a block.
    *   **Command:** `[TODO: This will be covered by an e2e or testnet test, but a manual CLI command would look like this]`
        ```bash
        # 1. Get a UTXO to spend
        # 2. Create and sign transaction
        # 3. Submit transaction
        # 4. Verify new UTXOs are created and old one is spent
        ```
    *   **Expected Outcome:** The transaction is successfully included in a block, and the UTXO set is updated correctly across all nodes.

## Phase 4: Advanced & Security Testing

This phase covers more complex scenarios and security-focused tests.

*   **[ ] 4.1: Run End-to-End (E2E) Tests**
    *   **Description:** Run the full E2E test suite, which covers complete user and system workflows.
    *   **Command:** `pytest tests/e2e/`
    *   **Expected Outcome:** All E2E tests should pass.

*   **[ ] 4.2: Execute Security Tests**
    *   **Description:** Run tests specifically designed to check for security vulnerabilities.
    *   **Command:** `pytest -m security`
    *   **Expected Outcome:** All security-focused tests should pass.

*   **[ ] 4.3: Execute Fuzzing Tests**
    *   **Description:** Run fuzz tests to bombard APIs and data processing functions with unexpected or random inputs.
    *   **Command:** `pytest tests/fuzzing/`
    *   **Expected Outcome:** The node should handle all inputs without crashing or entering an undefined state.

*   **[ ] 4.4: Execute Chaos Engineering Tests**
    *   **Description:** Run chaos tests that introduce random failures (e.g., stopping nodes, dropping network packets) to test network resilience.
    *   **Command:** `pytest tests/chaos/`
    *   **Expected Outcome:** The network should remain stable and continue to function correctly despite the induced chaos.

*   **[ ] 4.5: Run Performance Tests**
    *   **Description:** Run performance and benchmark tests. These are marked as `slow` and are skipped by default, so we must enable them explicitly.
    *   **Command:** `pytest -m performance --runslow`
    *   **Expected Outcome:** The tests should complete and report performance metrics. This helps track performance regressions.

## Phase 5: Custom XAI Module Testing

This phase tests the unique business logic of the XAI project.

*   **[ ] 5.1: AI Governance System Tests**
    *   **Description:** Run tests specifically for the AI Governance system.
    *   **Command:** `pytest tests/xai_tests/test_governance.py` (Assuming file name)
    *   **Expected Outcome:** All AI Governance tests should pass, confirming proposal, voting, and execution logic.

*   **[ ] 5.2: Smart Contract Engine Tests**
    *   **Description:** Run tests for the custom smart contract engine.
    *   **Command:** `pytest tests/xai_tests/test_smart_contracts.py` (Assuming file name)
    *   **Expected Outcome:** All smart contract engine tests should pass, including deployment, execution, and state changes.

## Phase 6: Cross-Chain & Interoperability Testing

*   **[ ] 6.1: Cross-Chain Asset Transfer**
    *   **Description:** Test atomic swaps with BTC, ETH, and DOGE as mentioned in the user's prompt. This will likely require a dedicated test setup and scripts.
    *   **Command:** `[TODO: To be defined based on atomic swap implementation details]`
    *   **Expected Outcome:** The atomic swap is completed successfully, with assets exchanged correctly between the chains.

## Phase 7: Monitoring & Auxiliary Services Testing

*   **[ ] 7.1: Verify Alerting System**
    *   **Description:** Run tests for the alerting system.
    *   **Command:** `pytest tests/alerting/`
    *   **Expected Outcome:** The alerting tests should pass, confirming that alerts are triggered and delivered correctly under specific conditions.

*   **[ ] 7.2: Verify Prometheus Metrics & Grafana Dashboards**
    *   **Description:** Check that the nodes are correctly exposing metrics and that the Grafana dashboards are configured.
    *   **Action:** Manually inspect the Grafana instance (likely at `http://localhost:3000`) to ensure dashboards are present and populating with data from the local testnet.
    *   **Expected Outcome:** Grafana dashboards are working and displaying key metrics like block height, transaction count, and peer connections.
