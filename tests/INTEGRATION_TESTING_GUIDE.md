# XAI Blockchain Comprehensive Integration Testing Guide

## Overview

This guide provides instructions for running the complete integration and end-to-end testing suite for the XAI blockchain. The test suite includes unit tests, integration tests, end-to-end tests, performance tests, and chaos tests.

## Directory Structure

```
tests/
├── xai_tests/
│   ├── integration/              # Integration tests
│   │   ├── test_multi_node_consensus.py
│   │   ├── test_chain_reorg.py
│   │   ├── test_network_partition.py
│   │   ├── test_transaction_propagation.py
│   │   ├── test_wallet_integration.py
│   │   └── test_governance.py
│   ├── performance/              # Performance benchmarks
│   │   ├── test_transaction_throughput.py
│   │   ├── test_block_validation.py
│   │   └── test_sync_performance.py
│   ├── security/                 # Security tests
│   ├── unit/                     # Unit tests
│   └── conftest.py               # Pytest fixtures
├── e2e/                          # End-to-end tests
│   ├── test_user_journey_mining.py
│   ├── test_user_journey_trading.py
│   ├── test_governance_flow.py
│   ├── test_smart_contract_deployment.py
│   └── test_multi_wallet_transfer.py
├── chaos/                        # Chaos testing
│   ├── test_node_failures.py
│   ├── test_network_delays.py
│   └── test_memory_pressure.py
└── conftest.py                   # Root fixtures
```

## Quick Start

### Prerequisites

```bash
# Install required packages
pip install -r requirements-dev.txt
pip install pytest pytest-cov pytest-xdist

# Navigate to project root
cd /path/to/crypto
```

### Run All Tests

```bash
# Run entire test suite with coverage
pytest tests/ -v --cov=src/xai --cov-report=html

# Run with specific markers
pytest tests/ -v -m "not slow"
```

## Test Categories

### 1. Integration Tests (tests/xai_tests/integration/)

Integration tests verify that multiple components work together correctly.

#### test_multi_node_consensus.py
Tests consensus reaching across 3+ nodes with proper block validation and synchronization.

**Run:**
```bash
pytest tests/xai_tests/integration/test_multi_node_consensus.py -v
```

**Test Cases:**
- `test_three_nodes_mine_same_height` - Verify nodes reach same block height
- `test_block_propagation_between_nodes` - Test block spreading
- `test_consensus_on_invalid_block` - Verify invalid block rejection
- `test_majority_consensus_longest_chain` - Test longest chain rule
- `test_consensus_with_transactions` - Consensus with transaction-containing blocks
- `test_double_spend_prevention` - Test double-spend prevention
- `test_fork_resolution` - Test fork handling
- `test_concurrent_mining_different_nodes` - Concurrent mining test
- `test_block_validation_across_nodes` - Validation consistency

#### test_chain_reorg.py
Tests blockchain reorganization scenarios during forks.

**Run:**
```bash
pytest tests/xai_tests/integration/test_chain_reorg.py -v
```

**Test Cases:**
- `test_simple_fork_resolution` - Basic fork resolution
- `test_deep_reorg` - Deep reorganization (multiple blocks)
- `test_reorg_with_transactions` - Reorg with transaction state
- `test_reorg_doesnt_lose_valid_txs` - Transaction preservation
- `test_very_deep_reorg` - Deep reorg (10+ blocks)
- `test_reorg_protection` - Reorg protection mechanisms

#### test_network_partition.py
Tests behavior during network partitions and splits.

**Run:**
```bash
pytest tests/xai_tests/integration/test_network_partition.py -v
```

**Test Cases:**
- `test_two_vs_one_partition` - 2 nodes vs 1 scenario
- `test_network_partition_recovery` - Recovery from partition
- `test_asymmetric_partition` - Asymmetric network state
- `test_majority_partition_continues` - Majority chain continues
- `test_partition_with_transactions` - Transaction handling in partition
- `test_prolonged_partition` - Extended partition handling

#### test_transaction_propagation.py
Tests transaction spreading across network nodes.

**Run:**
```bash
pytest tests/xai_tests/integration/test_transaction_propagation.py -v
```

**Test Cases:**
- `test_single_transaction_propagation` - Single tx spread
- `test_transaction_ordering` - Order preservation
- `test_transaction_confirmation` - Confirmation across network
- `test_double_spend_propagation` - Double-spend prevention
- `test_high_volume_transaction_propagation` - High volume handling
- `test_mempool_synchronization` - Mempool sync

#### test_wallet_integration.py
Complete wallet workflow testing.

**Run:**
```bash
pytest tests/xai_tests/integration/test_wallet_integration.py -v
```

**Test Cases:**
- `test_wallet_creation` - Wallet key generation
- `test_wallet_deterministic` - Key recovery
- `test_wallet_funding_simple` - Basic funding
- `test_wallet_send_receive` - Transaction flow
- `test_wallet_multiple_transactions` - Multiple txs
- `test_wallet_balance_tracking` - Accurate balance tracking
- `test_wallet_transaction_chain` - Transaction chains (A->B->C->D)
- `test_wallet_multi_node_sync` - Cross-node wallet state

### 2. End-to-End Tests (tests/e2e/)

E2E tests simulate real user workflows from start to finish.

#### test_user_journey_mining.py
User mining workflow: Start node -> Mine blocks -> Earn rewards

**Run:**
```bash
pytest tests/e2e/test_user_journey_mining.py -v
```

**Test Cases:**
- `test_user_starts_mining_node` - Basic mining setup
- `test_user_continuous_mining_session` - 10-block mining session
- `test_user_mining_with_pending_transactions` - Mining with txs
- `test_user_observes_block_reward_progression` - Reward tracking
- `test_user_long_mining_session_10_blocks` - Extended session
- `test_user_mining_then_transacting` - Mine then spend rewards

#### test_user_journey_trading.py
User trading workflow: Create wallet -> Receive funds -> Send -> Receive

**Run:**
```bash
pytest tests/e2e/test_user_journey_trading.py -v
```

**Test Cases:**
- `test_user_creates_wallet` - Wallet creation
- `test_user_receives_funds` - Receive transaction
- `test_user_complete_trading_flow` - Full flow (create->receive->send->receive)
- `test_user_multiple_transactions_same_day` - Multiple txs
- `test_user_trading_multiple_pairs` - Multi-wallet trading
- `test_user_trading_bidirectional` - Two-way trading

### 3. Performance Tests (tests/xai_tests/performance/)

Performance benchmarks for throughput and speed metrics.

#### test_transaction_throughput.py
Measures transactions per second (TPS) under load.

**Run:**
```bash
pytest tests/xai_tests/performance/test_transaction_throughput.py -v
```

**Test Cases:**
- `test_tps_10_transactions` - 10 tx throughput
- `test_tps_100_transactions` - 100 tx throughput
- `test_tps_1000_transactions` - 1000 tx throughput
- `test_block_mining_throughput` - Mining speed (blocks/sec)
- `test_mempool_throughput` - Mempool processing speed
- `test_sustained_throughput_100_blocks` - Sustained 100-block session
- `test_concurrent_transaction_creation` - Concurrent tx creation

**Performance Goals:**
- Minimum TPS: >10 for small transactions
- Block mining: >1 block/second
- Mempool processing: >100 TPS

#### test_block_validation.py
Block validation speed benchmarks.

**Run:**
```bash
pytest tests/xai_tests/performance/test_block_validation.py -v
```

#### test_sync_performance.py
Blockchain sync speed (10,000 blocks benchmark).

**Run:**
```bash
pytest tests/xai_tests/performance/test_sync_performance.py -v
```

### 4. Chaos Tests (tests/chaos/)

Chaos and failure injection tests for resilience.

#### test_node_failures.py
Tests recovery from various failure modes.

**Run:**
```bash
pytest tests/chaos/test_node_failures.py -v
```

**Test Cases:**
- `test_node_restart_recovery` - Restart recovery
- `test_graceful_shutdown_recovery` - Graceful shutdown
- `test_node_crash_recovery` - Crash recovery
- `test_corrupt_block_handling` - Corruption handling
- `test_multiple_node_failures` - Multiple failures
- `test_random_block_creation_failures` - Random failures
- `test_high_pending_transaction_load` - Load stress
- `test_rapid_block_succession` - Rapid mining stress
- `test_concurrent_operations_stress` - Concurrency stress

**Failure Scenarios:**
- Node crashes
- Database corruption
- Missing blocks
- Network failures
- Transaction failures
- Memory pressure

## Running Test Combinations

### Run All Integration Tests
```bash
pytest tests/xai_tests/integration/ -v --tb=short
```

### Run All E2E Tests
```bash
pytest tests/e2e/ -v --tb=short
```

### Run All Performance Tests
```bash
pytest tests/xai_tests/performance/ -v --tb=short
```

### Run All Chaos Tests
```bash
pytest tests/chaos/ -v --tb=short
```

### Run Specific Test Class
```bash
pytest tests/xai_tests/integration/test_multi_node_consensus.py::TestMultiNodeConsensus -v
```

### Run Specific Test Method
```bash
pytest tests/xai_tests/integration/test_multi_node_consensus.py::TestMultiNodeConsensus::test_three_nodes_mine_same_height -v
```

## Test Configuration

### pytest.ini
The project includes pytest.ini configuration:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Running with Coverage

```bash
# Generate coverage report
pytest tests/ --cov=src/xai --cov-report=html

# View HTML report
open htmlcov/index.html
```

### Running with Markers

```bash
# Run only fast tests
pytest tests/ -m "not slow" -v

# Run only integration tests
pytest tests/xai_tests/integration/ -v

# Run only performance tests
pytest tests/xai_tests/performance/ -v
```

## Interpreting Test Results

### Success Criteria

| Test Category | Success Criteria |
|---|---|
| Consensus | All nodes reach same block height |
| Reorg | Chain recovers correctly after fork |
| Network Partition | Nodes recover consensus after partition |
| Transactions | All txs confirmed within 2 blocks |
| Wallet | Balances accurate to satoshi |
| E2E Mining | Rewards accumulate correctly |
| E2E Trading | Balances match ledger perfectly |
| TPS | >10 txs/second minimum |
| Chaos Recovery | System recovers from all failures |

### Common Issues

#### Tests timeout
- Increase pytest timeout: `pytest --timeout=300`
- Check system resources
- Run fewer tests in parallel

#### Flaky tests
- Increase timing margins in race conditions
- Run tests multiple times: `pytest --count=5`
- Check for external dependencies

#### Memory issues
- Reduce test data size
- Run tests serially: `pytest -n0`
- Check for memory leaks

## Continuous Integration

### Run Full Test Suite
```bash
# Run all tests with coverage
pytest tests/ -v --cov=src/xai --cov-report=term-missing --cov-report=html --tb=short

# Run with parallel execution (faster)
pytest tests/ -v -n auto --cov=src/xai
```


Tests run automatically on:
- Pull requests
- Commits to main branch
- Scheduled nightly runs


## Test Maintenance

### Adding New Tests

1. Create test file in appropriate directory
2. Follow naming convention: `test_*.py`
3. Use fixtures from `conftest.py`
4. Add docstrings explaining test purpose
5. Include success/failure assertions

### Updating Existing Tests

1. Run tests before modification
2. Make minimal changes
3. Verify tests still pass
4. Update comments/docstrings if needed

### Test Data Management

- Use pytest fixtures for test data
- Fixtures in `conftest.py` for shared setup
- Use `tmp_path` for temporary files
- Clean up resources in fixture teardown

## Performance Benchmarks

### Expected Performance Metrics

| Metric | Target | Current |
|---|---|---|
| Transaction Creation | >100/sec | TBD |
| Block Mining | >1/sec | TBD |
| Block Validation | <100ms | TBD |
| Chain Sync (1000 blocks) | <5 sec | TBD |
| Double-spend Prevention | 100% | TBD |
| Network Partition Recovery | <10 blocks | TBD |
| Node Restart Time | <5 sec | TBD |

## Troubleshooting

### Test Failures

1. **Run failing test in isolation:**
   ```bash
   pytest tests/path/to/test.py::TestClass::test_method -v -s
   ```

2. **Check test output:**
   - Look for assertion failures
   - Check blockchain state at failure
   - Review balance tracking

3. **Verify blockchain state:**
   ```python
   # In test
   assert blockchain.validate_chain()
   print(f"Chain height: {len(blockchain.chain)}")
   print(f"Pending txs: {len(blockchain.pending_transactions)}")
   ```

### Debugging

Enable debug output:
```bash
pytest tests/ -v -s --log-cli-level=DEBUG
```

Use pytest debugger:
```bash
pytest tests/ --pdb  # Drop to debugger on failure
```

## Next Steps

1. Run the complete test suite
2. Review test coverage report
3. Address any failing tests
4. Set up CI/CD pipeline
5. Monitor test performance over time
6. Add new tests for new features

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [XAI Blockchain Documentation](../docs/)
- [Test Coverage Report](../htmlcov/index.html)

## Support

For test-related issues:
1. Check this guide
2. Review test docstrings
4. Create new issue with test output
